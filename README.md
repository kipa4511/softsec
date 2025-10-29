# tatou
A web platform for pdf watermarking. This project is intended for pedagogical use, and contain security vulnerabilities. Do not deploy on an open network.

## Instructions

The following instructions are meant for a bash terminal on a Linux machine. If you are using something else, you will need to adapt them.

To clone the repo, you can simply run:

```bash
git clone https://github.com/Gsoftsec24/tatou.git
```

Note that you should probably fork the repo and clone your own repo.


### Run python unit tests

```bash
cd tatou/server

# Create a python virtual environement
python3 -m venv .venv

# Activate your virtual environement
. .venv/bin/activate

# Install the necessary dependencies
python -m pip install -e ".[dev]"
pip install pgpy
pip install pikepdf
pip install hypothesis
pip install pytest pytest-cov hypothesis

# Run the unit tests
PYTHONPATH=./src pytest -vv
# For some API test cases a test user is required, Those test cases can be marked to failed initially. In that case after deployment create a user : test123@gmail.com and password : test123 and rerun the test. Make the test user is deleted after the test.
```

### Deploy

From the root of the directory:

```bash
# Create a file to set environement variables like passwords.
cp sample.env .env

# Edit .env and pick the passwords you want

# Rebuild the docker image and deploy the containers
docker compose up --build -d

# Monitor logs in realtime 
docker compose logs -f

# Test if the API is up
http -v :5000/healthz

# Open your browser at 127.0.0.1:5000 to check if the website is up.

Private Key placement (in root directory): Add you private key for RMAP authentication in /keys/server_priv.asc
```



