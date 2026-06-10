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

**Important:** the Dockerised frontend is served *through* QCrBox's Traefik reverse proxy and authenticates users via QCrBox's Authelia single sign-on.  This means:

- The QCrBox stack must be running *before* the frontend is started (the frontend joins QCrBox's `qcrbox_qcrbox-net` docker network).
- The frontend is reached at `https://<QCRBOX_DOMAIN>` (e.g. `https://localhost.local` for local setups), not on a port of its own.
- The required `/etc/hosts` entries and the end-to-end walkthrough are described in QCrBox's how-to guide ["Spinning up the full QCrBox stack locally"](https://github.com/QCrBox/QCrBox/blob/dev/docs/how_to_guides/spin_up_full_stack_locally.md).

## Dockerised Setup

The Dockerised Setup for QCrBox Frontend is designed to be a quick and portable way to get the web app up and running on any machine without having to worry too much about the host machine's environment.  The steps for setting up the Dockerised version are as follows:

1. Ensure that `docker` is installed on the deployment machine (see [www.docker.com/](https://www.docker.com/) for more information on Docker)
2. Navigate to [`QCrBox_Frontend/`](..), e.g. the folder containing this repository.
3. Copy the environment template with `cp environment.env.template environment.env`
4. Edit the settings `environment.env` to be used in your Dockerised deployment. For most cases, you should only need to edit `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_PASSWORD`, and the other values can be left as the defaults copied from the template.  **Note:** If you do not set these values, no user will be created at setup and you will have to create one manually by directly interfacing with the django inside the container.

The full list of settings is as follows:

    | Setting | Description |
    | --- | --- |
    | `DJANGO_DB` | Determines the architecture of the database used to store metadata for the frontend.  Can be set to either `'postgresql'` or `'sqlite'` |
    | `POSTGRES_HOST` | The host location for the database if `DJANGO_DB` is set to `'postgres'`.  This should be set to `'db'` for Docker deployments. |
    | `POSTGRES_NAME` | The name of the Postgres instance.  This should be set to `postgres`. |
    | `POSTGRES_USER` | The username for Postgres access.  This should be set to `'postgres'`. |
    | `POSTGRES_PASSWORD` | The password for Postgres access.  This should be set to `'postgres'`. |
    | `POSTGRES_PORT` | The port through which the Postgres is exposed.  This should be set to `5432`. |
    | `API_BASE_URL` | The URL by which the QCrBox registry API is reached from inside the frontend's `server` container.  This should be set to `'http://qcrbox-registry:8000'`, i.e. direct access over the shared docker network. |
    | `QCRBOX_DOMAIN` | The domain QCrBox is served under.  Must match `QCRBOX_DOMAIN` in the QCrBox stack's `.env` file (`localhost.local` for local setups). |
    | `ALLOWED_HOSTS` | Comma-separated list of hostnames Django accepts requests for.  Normally the same as `QCRBOX_DOMAIN`. |
    | `CSRF_TRUSTED_ORIGINS` | Comma-separated list of trusted origins, e.g. `https://localhost.local`. |
    | `AUTHELIA_SSO` | Set to `True` to log users in from the `Remote-User` header set by Authelia via Traefik (single sign-on).  Only enable when the frontend is reachable exclusively through the reverse proxy. |
    | `AUTHELIA_LOGOUT_URL` | Where the logout button sends users to end the Authelia session, e.g. `https://auth.localhost.local/logout`. |
    | `TRAEFIK_HTTP_PORT` | The port the reverse proxy serves HTTPS on.  Leave empty for the default port 443. |
    | `GUI_DOMAIN_PREFIX` | The prefix for GUI subdomains.  This should be set to `.gui.` for default setups. |
    | `MAX_LENGTH_API_LOG` | The maximum length of API output to be saved in the logs.  As some API outputs can be quite long, this gives the option to truncate them in the logs, making the logs more unwieldy at the cost of losing some debug information. |
    | `DJANGO_SUPERUSER_EMAIL` | The email address for the default admin account to be created for the web app. |
    | `DJANGO_SUPERUSER_USERNAME` | The username for the default admin account to be created for the web app. |
    | `DJANGO_SUPERUSER_PASSWORD` | The password for the default admin account to be created for the web app. |
5. Make sure the QCrBox stack is running (see Pre-Setup); the frontend joins its docker network.
6. Build and run the containers with `docker compose up -d --build`.
7. Open your choice of browser and navigate to your deployment URL; for local deployment, this URL will be [`https://localhost.local/`](https://localhost.local/) (accept the self-signed-certificate warning on local setups).
8. Log in at the Authelia portal you are redirected to (development default: `admin` / `changeme`, managed in QCrBox's `services/core/qcrbox_auth/users_database.yml`).  A matching frontend user is created automatically on first visit.  The `DJANGO_SUPERUSER_*` account from step 4 is only needed for the Django admin interface at `/admin`.
9. Navigate the Groups in the navigation bar and create at least one group (you will not be able to upload any data until you have created a group to assign it to).
10. Enjoy using QCrBox Frontend!

## Non-Dockerised Setup

You may also install QCrBox Frontend in a non-Dockerised way through the use of virtual environments, but this is neither portable nor secure and hence is only recommended for development purposes.  In this setup the app is served directly (not through Traefik/Authelia), so the Authelia single sign-on stays disabled (`AUTHELIA_SSO` defaults to `False`) and the frontend's own login page is used instead.  To install QCrBox Frontend in this way:

1. Navigate to [`QCrBox_Frontend/`](..), e.g. the folder containing this repository.
2. Create and activate a local Python virtual environment.  This environment must be based on python version `python>=3.11`.
3. Install the requirements into the virtual environment with `pip install -r requirements.txt`.
4. Navigate to [`qcrbox_frontend/`](../qcrbox_frontend) (e.g. `cd qcrbox_frontend`).
5. Set up the database with `python manage.py migrate`.  By default, this database will be an instance of SQLite.  This and other settings can be manually changed in this software's settings file found at [`qcrbox_frontend/core/settings.py`](../qcrbox_frontend/core/settings.py).
6. Create a site admin with `python manage.py createsuperuser`.
7. Collect staticfiles (e.g. css required to render plotly plots) with `python manage.py collectstatic`.
8. Start the server with `python manage.py runserver`.
9. Open your choice of browser and navigate to your deployment URL; by default, this URL will be [`http://localhost:8000/`](http://localhost:8000/).
10. Log in to the app using the credentials you set in step 6.
11. Navigate the Groups in the navigation bar and create at least one group (you will not be able to upload any data until you have created a group to assign it to).
12. Enjoy using QCrBox Frontend!

For more information, please check the documentation readme at [`QCRBox_Frontend/documentation/README.md`](./README.md)
