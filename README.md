# How to run the program

- In the thesis directory, create a python virtual env: `python3 -mvenv venv`
- `./venv/bin/pip install -e src/python-generator/`
- `./venv/bin/pip install -r src/python-generator/requirements.txt`
- `bash run-app.sh sas-files/<sas-file-name>`: this generate cpp files, compiles the program and runs it. The output plan is saved to `planner_plan` file.
