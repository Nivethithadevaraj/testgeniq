const hooks = require("hooks");
const http = require("http");

const BASE = "http://127.0.0.1:8000";

/*
 * TestGenIQ Dredd hooks (post-submission revision).
 *
 * Dredd generates one transaction for EVERY response code documented
 * in the contract (200, 400, 404, 422), but by default it sends the
 * same valid example request to all of them. A valid request can never
 * produce 400/404/422, so those transactions always failed.
 *
 * These hooks turn each transaction into a real scenario:
 *   2xx -> valid request against freshly created test data
 *   400 -> request that breaks a business rule (e.g. invalid priority)
 *   404 -> request for a resource that does not exist
 *   422 -> request that fails FastAPI schema validation
 *
 * The target API stores data in memory, so every positive scenario
 * creates its own task/user instead of relying on fixed IDs such as
 * /tasks/1 or a shared "testuser" account.
 */

const MISSING_TASK_ID = 999999;
const MISSING_USER = "no_such_user_zzz";
const PASSWORD = "dreddpass123";

let counter = 0;

function uniqueName(prefix) {
    counter += 1;
    return `${prefix}_${Date.now()}_${counter}`;
}

function request(method, path, body) {
    return new Promise((resolve) => {
        const data = body ? JSON.stringify(body) : null;

        const req = http.request(
            BASE + path,
            {
                method: method,
                headers: data
                    ? {
                        "Content-Type": "application/json",
                        "Content-Length": Buffer.byteLength(data)
                    }
                    : {}
            },
            (res) => {
                let responseBody = "";

                res.on("data", (chunk) => {
                    responseBody += chunk;
                });

                res.on("end", () => {
                    resolve({
                        status: res.statusCode,
                        body: responseBody
                    });
                });
            }
        );

        req.on("error", () => resolve({ status: 0, body: "" }));

        if (data) {
            req.write(data);
        }

        req.end();
    });
}

async function createTask() {
    const response = await request("POST", "/tasks", {
        title: "Dredd Fixture Task",
        description: "Created automatically for contract validation",
        priority: "medium"
    });

    try {
        return JSON.parse(response.body).id;
    } catch (error) {
        hooks.log("Dredd fixture warning: could not create task");
        return MISSING_TASK_ID;
    }
}

async function createUser() {
    const username = uniqueName("dredd_user");
    await request("POST", "/auth/register", {
        username: username,
        password: PASSWORD
    });
    return username;
}

function setPath(transaction, path) {
    transaction.fullPath = path;
    transaction.request.uri = path;
}

function setBody(transaction, body) {
    transaction.request.body = JSON.stringify(body);
    transaction.request.headers["Content-Type"] = "application/json";
}

function resourceOf(transaction) {
    // Transaction names look like:
    // "/tasks/{task_id} > Api Get Task > 200 > application/json"
    return (transaction.name || "").split(" > ")[0];
}


hooks.beforeEach(async function (transaction, done) {

    const resource = resourceOf(transaction);
    const method = transaction.request.method;
    const status = String(transaction.expected.statusCode);

    try {

        if (transaction.request.body === undefined) {
            transaction.request.body = "";
        }

        // -------------------------------------------------
        // POST /tasks
        // -------------------------------------------------
        if (resource === "/tasks" && method === "POST") {
            if (status === "200") {
                setBody(transaction, {
                    title: "Dredd Created Task",
                    description: "Contract test task",
                    priority: "medium"
                });
            } else if (status === "400") {
                // Business rule: priority must be low/medium/high
                setBody(transaction, {
                    title: "Invalid Priority Task",
                    priority: "critical"
                });
            } else if (status === "422") {
                // Schema rule: title is required
                setBody(transaction, { description: "missing title" });
            }
        }

        // -------------------------------------------------
        // /tasks/{task_id}  (GET, PUT, DELETE)
        // -------------------------------------------------
        else if (resource === "/tasks/{task_id}") {
            if (status === "200" || status === "400") {
                const id = await createTask();
                setPath(transaction, `/tasks/${id}`);
            } else if (status === "404") {
                setPath(transaction, `/tasks/${MISSING_TASK_ID}`);
            } else if (status === "422") {
                // Schema rule: task_id must be an integer
                setPath(transaction, "/tasks/not-a-number");
            }

            if (method === "PUT") {
                if (status === "400") {
                    // Business rule: title cannot be blank
                    setBody(transaction, { title: "   " });
                } else {
                    setBody(transaction, {
                        title: "Dredd Updated Task",
                        completed: false
                    });
                }
            }
        }

        // -------------------------------------------------
        // POST /auth/register
        // -------------------------------------------------
        else if (resource === "/auth/register") {
            if (status === "200") {
                setBody(transaction, {
                    username: uniqueName("dredd_register"),
                    password: PASSWORD
                });
            } else if (status === "400") {
                // Business rule: password must be at least 6 characters
                setBody(transaction, {
                    username: uniqueName("dredd_short"),
                    password: "12345"
                });
            } else if (status === "422") {
                // Schema rule: password is required
                setBody(transaction, { username: "dredd_missing_password" });
            }
        }

        // -------------------------------------------------
        // POST /auth/login
        // -------------------------------------------------
        else if (resource === "/auth/login") {
            if (status === "200") {
                const username = await createUser();
                setBody(transaction, { username: username, password: PASSWORD });
            } else if (status === "400") {
                // Business rule: wrong password is rejected
                const username = await createUser();
                setBody(transaction, {
                    username: username,
                    password: "wrong-password"
                });
            } else if (status === "422") {
                // Schema rule: password is required
                setBody(transaction, { username: "dredd_missing_password" });
            }
        }

        // -------------------------------------------------
        // /users/{username} and /users/{username}/deactivate
        // -------------------------------------------------
        else if (resource.startsWith("/users/{username}")) {
            const suffix = resource.endsWith("/deactivate") ? "/deactivate" : "";

            if (status === "200") {
                const username = await createUser();
                setPath(transaction, `/users/${username}${suffix}`);
            } else if (status === "404") {
                setPath(transaction, `/users/${MISSING_USER}${suffix}`);
            } else if (status === "422") {
                // A string path parameter cannot fail schema validation,
                // so this documented 422 response is not reachable.
                transaction.skip = true;
                hooks.log(
                    `Skipped unreachable 422 scenario: ${transaction.name}`
                );
            }
        }

    } catch (error) {
        hooks.log(
            "Dredd fixture setup warning: " + error.message
        );
    }

    done();
});


/*
 * FastAPI's HTTPValidationError, exactly as documented in openapi.json
 * (components/schemas/ValidationError): only loc, msg and type are
 * required. Dredd's OpenAPI 3 adapter wrongly marks the optional "ctx"
 * property as required, so 422 bodies are validated against this
 * contract-accurate schema instead.
 */
const HTTP_VALIDATION_ERROR_SCHEMA = {
    type: "object",
    required: ["detail"],
    properties: {
        detail: {
            type: "array",
            items: {
                type: "object",
                required: ["loc", "msg", "type"],
                properties: {
                    loc: { type: "array" },
                    msg: { type: "string" },
                    type: { type: "string" }
                }
            }
        }
    }
};


/*
 * Responses documented without a body (400/404 here) are checked
 * on status code only. Responses with a documented schema (200, 422)
 * keep their real body so Dredd validates it against the contract.
 */
hooks.beforeEachValidation(function (transaction, done) {

    const expected = transaction.expected || {};

    if (String(expected.statusCode) === "422") {
        expected.bodySchema = HTTP_VALIDATION_ERROR_SCHEMA;
        delete expected.body;
    }

    if (
        !expected.bodySchema &&
        !expected.body &&
        transaction.real
    ) {
        transaction.real.body = "";
    }

    done();
});
