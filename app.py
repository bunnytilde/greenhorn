import requests, sys, os, logging, json, py7zr, base64, csv
import hashlib
import pandas as pd
import subprocess

# Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("debug.log"), logging.StreamHandler(sys.stdout)],
)
config = None
config_filename = "vrp-public.json"
gamelist_filename = "VRP-GameList.txt"
rclone_games_folder = "Quest Games"


# Function to retrieve config, that contains http endpoint and metadata password
def getConfig():
    global config, config_filename
    if not os.path.isfile(config_filename):
        config_dl = requests.get(
            "https://wiki.vrpirates.club/downloads/vrp-public.json"
        )
        if config_dl.status_code == 200:
            open(config_filename, "w").write(config_dl.text)
            config = json.loads(config_dl.text)
            return True
        else:
            logging.error("Unable to download the config!")
            return False
    else:
        config = json.loads(open(config_filename, "r").read())


# Function to download metadata from endpoint and extract it (7z archive with password)
def getMetadata():
    global config
    logging.info("Downloading metadata...")
    # Creating rclone command and executing it
    rclone_cmd = f"rclone copy \":http:meta.7z\" \"metadata.7z\" --http-url {config['baseUri']} --rc"
    logging.info(f"Starting rclone with command {rclone_cmd}")
    rclone_process = subprocess.Popen(rclone_cmd, shell=True)
    rclone_process_exit_code = rclone_process.wait()
    logging.info(f"{rclone_cmd} exited with code {rclone_process_exit_code}")

    logging.info("Extracting metadata...")
    with py7zr.SevenZipFile(
        "metadata.7z", "r", password=metadata_password
    ) as archive:
        archive.extractall(path=".")


# Helper function, to display all applications from metadata, just using pandas
def readMetadata():
    df = pd.read_csv(gamelist_filename, sep=";")
    print(df.to_string())


# We can download game by its releaseName from CSV
# Title is MD5 encoded with "x2" appended to the end of hash
def downloadGame(releaseName):
    global config, metadata_password
    # releaseName hash containes releaseName + newline
    gameNameHash = str(hashlib.md5((releaseName + "\n").encode()).hexdigest())
    logging.info(f"releasename hash: {gameNameHash}")

    # Checking if directories exists
    if not os.path.isdir("downloads"):
        os.mkdir("downloads")

    if not os.path.isdir(f"downloads/{releaseName}"):
        os.mkdir(f"downloads/{releaseName}")

    # Creating rclone command and executing it
    rclone_cmd = f"rclone copy \":http:{gameNameHash}\" \"downloads/{releaseName}\" --http-url {config['baseUri']} --rc"
    logging.info(f"Starting rclone with command {rclone_cmd}")
    rclone_process = subprocess.Popen(rclone_cmd, shell=True)
    rclone_process_exit_code = rclone_process.wait()
    logging.info(f"{rclone_cmd} exited with code {rclone_process_exit_code}")
    
    if rclone_process_exit_code == 0:
        logging.info("Extracting files...")
        # If download was successful, combaining archive parts and extracting it
        archive_parts = [f for f in os.listdir(f"downloads/{releaseName}") if os.path.isfile(os.path.join(f"downloads/{releaseName}", f))]
        with open(f'downloads/{releaseName}/out.7z', 'ab') as outfile:
            for part in archive_parts:
                with open(f'downloads/{releaseName}/{part}', 'rb') as infile:
                    outfile.write(infile.read())
        with py7zr.SevenZipFile(f'downloads/{releaseName}/out.7z', 'r', password=metadata_password) as archive:
            archive.extractall(path=f"downloads/")
        os.unlink(f'downloads/{releaseName}/out.7z')
        logging.info("Done!")
    else:
        logging.warning('An error occured while trying to download archive from mirror!')

# pseudo menu
def menu():
    app_id = int(input("Provide a ID of application you want to download: "))
    with open(gamelist_filename) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=";")
        rows = list(csv_reader)
        logging.info(f"Selected game: {rows[app_id]}")
        downloadGame(rows[app_id][1])


getConfig()
metadata_password = base64.b64decode(config["password"]).decode("utf-8")
getMetadata()
readMetadata()
menu()
