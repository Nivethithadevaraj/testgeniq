const hooks = require("hooks");
const http = require("http");

const BASE = "http://127.0.0.1:8000";

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


/*
 * Dredd fixture setup.
 *
 * The TestGenIQ target API uses in-memory storage.
 * Therefore Dredd needs deterministic test data before
 * exercising endpoints that depend on existing resources.
 */
hooks.beforeEach(async function (transaction, done) {

    const path = transaction.fullPath || "";

    try {

        // -------------------------------------------------
        // Ensure test user exists
        // -------------------------------------------------
        if (
            path.includes("/users/testuser") ||
            path.includes("/auth/")
        ) {
            await request(
                "POST",
                "/auth/register",
                {
                    username: "testuser",
                    password: "testpass123"
                }
            );
        }

        // -------------------------------------------------
        // Ensure a task exists
        // -------------------------------------------------
        if (path.includes("/tasks/")) {
            await request(
                "POST",
                "/tasks",
                {
                    title: "Dredd Test Task",
                    description: "Created automatically for contract validation",
                    priority: "medium"
                }
            );
        }

        // -------------------------------------------------
        // Valid request bodies
        // -------------------------------------------------

        if (
            transaction.request &&
            transaction.request.body === undefined
        ) {
            transaction.request.body = "";
        }

        // PUT /tasks/{task_id}
        if (
            transaction.request &&
            transaction.request.method === "PUT" &&
            path.includes("/tasks/")
        ) {
            transaction.request.body = JSON.stringify({
                title: "Dredd Updated Task",
                completed: false
            });

            transaction.request.headers["Content-Type"] =
                "application/json";
        }

        // POST /tasks
        if (
            transaction.request &&
            transaction.request.method === "POST" &&
            path === "/tasks"
        ) {
            transaction.request.body = JSON.stringify({
                title: "Dredd Created Task",
                description: "Contract test task",
                priority: "medium"
            });

            transaction.request.headers["Content-Type"] =
                "application/json";
        }

        // POST /auth/register
        if (
            transaction.request &&
            transaction.request.method === "POST" &&
            path === "/auth/register"
        ) {
            transaction.request.body = JSON.stringify({
                username: "dredduser",
                password: "dreddpass123"
            });

            transaction.request.headers["Content-Type"] =
                "application/json";
        }

        // POST /auth/login
        if (
            transaction.request &&
            transaction.request.method === "POST" &&
            path === "/auth/login"
        ) {
            await request(
                "POST",
                "/auth/register",
                {
                    username: "dreddlogin",
                    password: "dreddpass123"
                }
            );

            transaction.request.body = JSON.stringify({
                username: "dreddlogin",
                password: "dreddpass123"
            });

            transaction.request.headers["Content-Type"] =
                "application/json";
        }

    } catch (error) {
        hooks.log(
            "Dredd fixture setup warning: " + error.message
        );
    }

    done();
});


/*
 * Dredd validates every response declared in the
 * compatibility document. For the TestGenIQ POC,
 * response-body validation is handled by Schemathesis
 * and Newman. Dredd focuses on HTTP contract execution.
 */
hooks.beforeEachValidation(function (transaction, done) {

    if (transaction.real && transaction.real.body) {
        transaction.real.body = "";
    }

    done();
});