python -m pytest --cov=app --cov=engine --cov-report=term-missing --cov-report=html
python generate_tests.py
python run_testgeniq.py
