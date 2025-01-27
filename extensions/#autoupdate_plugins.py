import os
import requests
import re
import json
from typing import Union

from daemon import *
from extensions.download_github_release import GitHubDownloader
from extensions.minecraft import MINECRAFT_PROXY_DIR

SPIGET_PLUGINS = [
    (19254, "ViaVersion.jar"),
    (27448, "ViaBackwards.jar"),
    (52109, "ViaRewind.jar")
]

GITHUB_PLUGINS = [
    ("CakeDreamer/ProxiedProxy", "ProxiedProxy.jar"),
    ("MUAlliance/UnionProxyExtension", "UnionProxyExtension.jar")
]

STORAGE_FILE = "autoupdate_plugins.txt"

class SpigetPluginAutoUpdater:
    def __init__(self, plugins : list[str]):
        DAEMON.eventMgr.registerHandler(DaemonStartEvent, self.onDaemonInit, Event.Priority.HIGH)
        self.plugins = plugins

    def onDaemonInit(self, event : DaemonStartEvent) -> None:
        INFO("Checking for Spiget plugins updates...")
        for resource_id, jar_file in SPIGET_PLUGINS:
            self.download(resource_id, os.path.join(MINECRAFT_PROXY_DIR, "plugins", jar_file))

    def download(self, resource_id : str, save_path : str) -> None:
        BASE_URL = 'https://api.spiget.org/v2/resources'
        DOWNLOAD_URL = '{}/{}/download'.format(BASE_URL, resource_id)
        try:
            response = requests.get(DOWNLOAD_URL, stream=True)
            
            if not os.path.exists(os.path.dirname(save_path)):
                os.makedirs(os.path.dirname(save_path))
            
            # Check SHA1 of the local file if it exists
            if os.path.exists(save_path):
                with open(save_path, 'rb') as file:
                    local_sha1 = hashlib.sha1(file.read()).hexdigest()
            else:
                local_sha1 = None
            
            # Check SHA1 of the remote file
            # For external resources, there is no SHA1 or any other digest header available,
            # so maybe we should find another approach to do this
            remote_sha1 = response.headers.get('X-Spiget-Resource-SHA1')

            # Continue download if file doesn't exist locally or SHA1 mismatch or remote SHA1 is not available
            if remote_sha1 == None or local_sha1 != remote_sha1:
                if response.status_code == 200:
                    with open(save_path, 'wb') as file:
                        file.write(response.raw.read())
                        
                    INFO(f'Download completed. File saved to: {save_path}')
                else:
                    WARN(f'Unable to download the plugin. Status code: {response.status_code}')
            else:
                WARN(f'File already exists locally with matching SHA1: {local_sha1}')
        except Exception as e:
            WARN(f'An error occurred while downloading the plugin: {str(e)}')
        
class GithubPluginAutoUpdater:
    def __init__(self, plugins : list[str]):
        DAEMON.eventMgr.registerHandler(DaemonStartEvent, self.onDaemonInit, Event.Priority.HIGH)
        self.plugins = plugins
        self.downloaded_ids = {}
        self.downloaded_ids_new = {}

    def onDaemonInit(self, event : DaemonStartEvent) -> None:
        INFO("Checking for Github plugins updates...")
        if not os.path.exists(os.path.join("extensions", "conf")):
            os.makedirs(os.path.join("extensions", "conf"))
        if not os.path.exists(os.path.join("extensions", "conf", STORAGE_FILE)):
            open(os.path.join("extensions", "conf", STORAGE_FILE), 'w').close()
        with open(os.path.join("extensions", "conf", STORAGE_FILE), 'r') as f:
            try:
                self.downloaded_ids = json.load(f)
            except:
                self.downloaded_ids = {}
        for item in GITHUB_PLUGINS:
            if len(item) == 2:
                repo, output = item
                keyword = ".jar$"
            elif len(item) == 3:
                repo, output, keyword = item
            else:
                continue
            try:
                self.download(repo, keyword, os.path.join(MINECRAFT_PROXY_DIR, "plugins", output))
            except:
                WARN("Download failed.")
        with open(os.path.join("extensions", "conf", STORAGE_FILE), 'w') as f:
            json.dump(self.downloaded_ids_new, f)

    def download(self, repo : str, keyword : Union[str, re.Pattern, None], output : str) -> None:
        resource = GitHubDownloader(repo).search(None, keyword)
        if resource.getId() != 0:
            if self.downloaded_ids.get(output, 0) != resource.getId():
                resource.download(os.path.dirname(output), os.path.basename(output))
                INFO(f"{repo} downloaded as: {output}")
            else:
                INFO(f"{repo} is the latest.")
            self.downloaded_ids_new[output] = resource.getId()

SpigetPluginAutoUpdater(SPIGET_PLUGINS)
GithubPluginAutoUpdater(GITHUB_PLUGINS)