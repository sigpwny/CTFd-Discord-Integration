# Project module imports
from CTFd.plugins import register_plugin_assets_directory, override_template

# External module imports
from flask import request, session, Blueprint, redirect
import os
import logging
import json

# Local module imports
from .discord_oauth import Discord_Oauth

# Global variables
# Used primarily due to flask routed functions being unable to use class "self" reflections
plugin_name = "Discord_Oauth"
log = logging.getLogger(plugin_name)
discord_oauth = None
discord_blueprint = Blueprint("discord_oauth", __name__, template_folder="assets")


def override_page(base_asset_path: str, page: str):
    """
    Overrides login page with custom login page with Discord Login button.

    :base_asset_path: Path to the plugin assets directory on the filesystem
    :page: Page to overwrite from the templates to actual
    :return: None
    """
    template_path = os.path.join(base_asset_path, page)
    try:
        override_template(page, open(template_path).read())
    except OSError:
        log.error("Unable to replace {} template".format(page))

# Routes
@discord_blueprint.route("/discord/oauth")
def discord_oauth_login():
    """
    Configures Discord Oauth and redirects to Discord Login

    :return: Redirect to Discord's OAuth2 login page
    """
    global discord_oauth
    log.debug("Session: [{}]".format(session))
    log.debug("OAuth: [{}]".format(str(discord_oauth)))
    return redirect(discord_oauth.gen_auth_url())


@discord_blueprint.route("/discord/oauth_callback")
def discord_oauth_callback():
    """
    Callback response configured to come from Discord's OAuth2 redirect

    :return: Redirect to users login home page (or error)
    """
    log.debug("Request: [{}]".format(request))
    log.debug("Session: [{}]".format(session))
    log.debug("OAuth Response Code: [{}]".format(request.args.get("code")))
    global discord_oauth
    token = discord_oauth.get_access_token(request.args.get("code"))
    log.debug("token= {}".format(token))
    user_json = discord_oauth.get_user_info(token)
    # process user info/login/etc
    return "userdata: " + str(user_json)


def check_debug_mode(debug: bool):
    """
    Checks for DEBUG mode and activates logger accordingly

    :debug: Variable to toggle debug or info
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Debug mode enabled.")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.debug("Log level {log_level} enabled.".format(logging.getEffectiveLevel()))


def load_config():
    """
    Loads plugin configuration file from disk

    :return: JSON object with config contents, or None if errored
    """
    conf_location = os.path.dirname(os.path.realpath(__file__)) + "/../config.json"

    try:
        with open(conf_location, "r") as conf_file:
            return json.load(conf_file)
    # EnvironmentError is wraps IOError, OSError, and WindowsError
    except EnvironmentError:
        log.error("Unable to load config file: [{}]".format(conf_location))
        return None


def string_to_bool(string: str):
    """
    :string: String to parse as boolean
    :return: True if string is "true" (case insensitive), false otherwise
    """
    if string.lower() == "true":
        return True
    else:
        return False


def setup_oauth(config):
    """
    Sets up the global variable "discord_oauth"
    """
    global discord_oauth
    global plugin_name
    discord_oauth = Discord_Oauth(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            scope=config["scope"],
            redirect_uri="https://{}/discord/oauth_callback".format(config["domain"]),
            discord_api_url=config["base_discord_api_url"],
            plugin_name=plugin_name
            )


# Load plugin into CTFd
def load(app):
    """
    Hook for CTFd to load the plugin

    :app: CTFd flask insert
    :return: None
    """
    # Basic Setup
    config = load_config()
    check_debug_mode(string_to_bool(config["debug"]))
    log.debug("Loaded config: [{}]".format(config))

    # OAuth setup
    setup_oauth(config)

    # Get plugin asset path
    base_asset_path = os.path.dirname(os.path.realpath(__file__)) + "/../assets/"
    register_plugin_assets_directory(app, base_path=base_asset_path)

    # Registration
    override_page(base_asset_path, "login.html")
    app.register_blueprint(discord_blueprint)
