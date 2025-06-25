# QCrBox Frontend Deployment Instructions

To deploy QCrBox Frontend, you have two options: Dockerised or non-Dockerised, which are both described below.  In each case, first follow the `pre-setup` instructions before moving onto the instructions specific to your chosen deployment method.

## Pre-Setup

Before setting up QCrBox Frontend, you will need to install the QCrBox.  Instructions for installing QCrBox can be found in it's repository at [`https://github.com/QCrBox/QCrBox`](https://github.com/QCrBox/QCrBox).
Once QCrBox is installed, use it to build the containers for the tools you intend to use, and make sure that these containers are running.  This can be done by, e.g., navigating to the QCrBox installation folder on your machine and running the following commands:

```
devbox shell
qcb build --all
qcb up --all
```

See the QCrBox documentation for more information on setting up QCrBox.

## Dockerised Setup

The Dockerised Setup for QCrBox Frontend is designed to be a quick and portable way to get the web app up and running on any machine without having to worry too much about the host machine's environment.  The steps for setting up the Dockerised version are as follows:

1. Ensure that `docker` is installed on the deployment machine (see [www.docker.com/](https://www.docker.com/) for more information on Docker)
2. Navigate to [`QCrBox_Frontend/`](..), e.g. the folder containing this repository.
3. Copy the environment template with `cp environment.env.template environment.env`
4. Edit the settings `environment.env` to be used in your Dockerised deployment.  The settings are as follows:

| `DJANGO_DB` | Determines the architecture of the database used to store metadata for the frontend.  Can be set to either `'postgresql'` or `'sqlite'` |
| `POSTGRES_HOST` | The host location for the database if `DJANGO_DB` is set to `'postgres'`.  This should be set to `'db'` for Docker deployments. |
| `POSTGRES_NAME` | The name of the Postgres instance.  This should be set to `postgres`. |
| `POSTGRES_USER` | The username for Postgres access.  This should be set to `'postgres'`. |
| `POSTGRES_PASSWORD` | The password for Postgres access.  This should be set to `'postgres'`. |
| `POSTGRES_PORT` | The port through which the Postgres is exposed.  This should be set to `5432`. |
| `API_BASE_URL` | The URL and port by which the QCrBox tool manager can be accessed.  If QCrBox is installed on the same machine as this setup, this should be set to `'http://host.docker.internal:11000'`. |
| `MAX_LENGTH_API_LOG` | The maximum length of API output to be saved in the logs.  As some API outputs can be quite long, this gives the option to truncate them in the logs, making the logs more unwieldy at the cost of losing some debug information. |
| `DJANGO_SUPERUSER_EMAIL` | The email address for the default admin account to be created for the web app. |
| `DJANGO_SUPERUSER_USERNAME` | The username for the default admin account to be created for the web app. |
| `DJANGO_SUPERUSER_PASSWORD` | The password for the default admin account to be created for the web app. |

For most cases, you should only need to edit `DJANGO_SUPERUSER_`, `DJANGO_SUPERUSER_` and `DJANGO_SUPERUSER_`, and the other values can be left as the defaults copied from the template.  **Note:** If you do not set these values, no user will be created at setup and you will have to create one manually by directly interfacing with the django inside the container.
5. Build the Docker container with `docker compose build`.
6. Run the Docker container with `docker compose up`.
7. Open your choice of browser and navigate to your deployment URL; for local deployment, this URL will be [`http://localhost:8888/`](http://localhost:8888/).
8. Log in to the app using the `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_PASSWORD` you set in step 4.
9. Enjoy using QCrBox Frontend!

## Non-Dockerised Setup

You may also install QCrBox Frontend in a non-Dockerised way through the use of virtual environments, but this is neither portable nor secure and hence is only recommended for development purposes.  To install QCrBox Frontend in this way:

1. Navigate to [`QCrBox_Frontend/`](..), e.g. the folder containing this repository.
2. Create and activate a local Python virtual environment.  This environment must be based on python version `python>=3.11`.
3. Install the requirements into the virtual environment with `pip install -R requirements.txt`.
4. Navigate to [`qcrbox_frontend/`](../qcrbox_frontend) (e.g. `cd qcrbox_frontend`).
5. Set up the database with `python manage.py migrate`.  By default, this database will be an instance of SQLite.  This and other settings can be manually changed in this software's settings file found at [`qcrbox_frontend/core/settings.py`](../qcrbox_frontend/core/settings.py).
6. Create a site admin with `python manage.py createsuperuser`.
7. Open your choice of browser and navigate to your deployment URL; by default, this URL will be [`http://localhost:8000/`](http://localhost:8000/).
8. Log in to the app using the credentuals you set in step 6.
9. Enjoy using QCrBox Frontend!

For more information, please check the documentation readme at [`QCRBox_Frontend/documentation/README.md`](./README.md)
