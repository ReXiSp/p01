from dicttoxml import dicttoxml
import bosscrypto
from dotenv import load_dotenv
from datetime import datetime
import pytz
import os
import traceback
from xml.dom.minidom import parseString
import copy
import logging
import shutil

# Shut up the dicttoxml log
logging.getLogger('dicttoxml').setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.INFO)

# Secret
load_dotenv()
BOSS_AES_KEY = os.getenv("BOSS_AES_KEY")
BOSS_HMAC_KEY = os.getenv("BOSS_HMAC_KEY")

# Constants
SPL_V16_SCHDATA = "schdata"
SPL_V16_OPTDATA = "optdata"
SPL_V16_TASKSHEET = [SPL_V16_SCHDATA, SPL_V16_OPTDATA]

SPL_V16_PATH = "src/"

# Splatoon
SPL_REGION_EUR = "zvGSM4kOrXpkKnpT"
SPL_REGION_USA = "rjVlM7hUXPxmYQJh"
SPL_REGION_JPN = "bb6tOEckvgZ50ciH"

SPL_REGION_MAP = {
    "JPN": SPL_REGION_JPN,
    "EUR": SPL_REGION_EUR,
    "USA": SPL_REGION_USA
}

SPL_REGION_LIST = [SPL_REGION_EUR, SPL_REGION_USA, SPL_REGION_JPN]

# Splatoon v16
SPL_TITLEID_EUR = "0005000010176a00"
SPL_TITLEID_USA = "0005000010176900"
SPL_TITLEID_JPN = "0005000010162c00"

SPL_V16_SPOOFURL = "https://rexisp.github.io/p01/content/"

SPL_TITLEID = {
    SPL_REGION_EUR: SPL_TITLEID_EUR,
    SPL_REGION_USA: SPL_TITLEID_USA,
    SPL_REGION_JPN: SPL_TITLEID_JPN,
}

SPL_TASKSHEET_TEMPLATE = {
    "TaskSheet": {
        "TitleId": "TITLE_ID",
        "TaskId": "TASK_ID",
        "ServiceStatus": "open",
        "Files": [
            # SPL_TASKSHEET_FILE_TEMPLATE
        ]
    }
}

SPL_TASKSHEET_FILE_TEMPLATE = {
    "Filename": "FILENAME",
    "DataId": 0,
    "Type": "AppData",
    "Url": "URL",
    "Size": 0,
    "Notify": {
        "New": "app",
        "LED": "false"
    }
}

spl_DataID = 0
bossDataMap = {
    SPL_REGION_EUR: {
        SPL_V16_SCHDATA: [
            {
                "fileName": "VSSetting.byaml",
                "path": SPL_V16_PATH
            }
        ],
        SPL_V16_OPTDATA: [
            {
                "fileName": "Festival3003.byaml",
                "path": SPL_V16_PATH + "EUR/"
            },
            {
                "fileName": "HapTexture3003.bfres",
                "path": SPL_V16_PATH + "EUR/"
            },
            {
                "fileName": "PanelTexture3003.bfres",
                "path": SPL_V16_PATH + "EUR/"
            }
        ],
    },
    SPL_REGION_JPN: {
        SPL_V16_SCHDATA: [
            {
                "fileName": "VSSetting.byaml",
                "path": SPL_V16_PATH
            }
        ],
        SPL_V16_OPTDATA: [
            {
                "fileName": "Festival1003.byaml",
                "path": SPL_V16_PATH + "JPN/"
            },
            {
                "fileName": "HapTexture1003.bfres",
                "path": SPL_V16_PATH + "JPN/"
            },
            {
                "fileName": "PanelTexture1003.bfres",
                "path": SPL_V16_PATH + "JPN/"
            }
        ]
    },
    SPL_REGION_USA: {
        SPL_V16_SCHDATA: [
            {
                "fileName": "VSSetting.byaml",
                "path": SPL_V16_PATH
            }
        ],
        SPL_V16_OPTDATA: [
            {
                "fileName": "Festival2003.byaml",
                "path": SPL_V16_PATH + "USA/"
            },
            {
                "fileName": "HapTexture2003.bfres",
                "path": SPL_V16_PATH + "USA/"
            },
            {
                "fileName": "PanelTexture2003.bfres",
                "path": SPL_V16_PATH + "USA/"
            }
        ],
    }
}

def is_v16_task(url: str) -> list:
    for region in SPL_REGION_LIST:
        for tasksheet in SPL_V16_TASKSHEET:
            if f"p01/tasksheet/1/{region}/{tasksheet}" in url:
                return [region, tasksheet]

    return ["", ""]

def get_bossdata(region: str, task: str):
    return bossDataMap[region][task]

def get_bossdata_from_name(region: str, name: str):
    for data in bossDataMap[region][SPL_V16_SCHDATA]:
        if data["fileName"] == name:
            return data
    for data in bossDataMap[region][SPL_V16_OPTDATA]:
        if data["fileName"] == name:
            return data
    return None

def make_fake_tasksheet(region: str, task: str):
    global spl_DataID
    bossData = get_bossdata(region, task)

    fakeDict = copy.deepcopy(SPL_TASKSHEET_TEMPLATE)
    fakeDict["TaskSheet"]["TitleId"] = SPL_TITLEID[region]
    fakeDict["TaskSheet"]["TaskId"] = task

    if "Files" not in fakeDict["TaskSheet"] or not isinstance(fakeDict["TaskSheet"]["Files"], list):
        fakeDict["TaskSheet"]["Files"] = []

    for boss in bossData:
        logging.info(f"Spoof for {boss['fileName']}")
        fileData = copy.deepcopy(SPL_TASKSHEET_FILE_TEMPLATE)
        fileData["DataId"] = spl_DataID
        spl_DataID += 1
        open(SPL_V16_PATH + ".id", "w").write(str(spl_DataID))
        fileData["Filename"] = boss["fileName"]
        fileData["Size"] = len(boss["raw"])
        fileData["Url"] = SPL_V16_SPOOFURL + region + "/" + boss["fileName"]
        fakeDict["TaskSheet"]["Files"].append(fileData)

    my_item_func = lambda x: "File"
    taskSheetXML = parseString(dicttoxml(fakeDict, root=False, attr_type=False, item_func=my_item_func)).toprettyxml(indent="", encoding="UTF-8", newl="")
    return [taskSheetXML.decode(), fakeDict]

def load_bossfiles():
    logging.info("Loading Boss Files...")
    for region in SPL_REGION_LIST:
        for task in SPL_V16_TASKSHEET:
            if task in bossDataMap[region]:
                for data in bossDataMap[region][task]:
                    try:
                        data["raw"] = bosscrypto.encrypt_wiiu(data["path"] + data["fileName"], BOSS_AES_KEY, BOSS_HMAC_KEY)
                        logging.info(f"Loaded {data['fileName']}")
                    except Exception as e:
                        traceback.print_exc()

def copy_bossfiles():
    logging.info("Copying Boss Files...")
    for region in SPL_REGION_LIST:
        for task in SPL_V16_TASKSHEET:
            if task in bossDataMap[region]:
                for data in bossDataMap[region][task]:
                    try:
                        raw = bosscrypto.encrypt_wiiu(data["path"] + data["fileName"], BOSS_AES_KEY, BOSS_HMAC_KEY)
                        os.makedirs(f"content/{region}/", exist_ok=True)
                        with open(f"content/{region}/{data['fileName']}", "wb") as f:
                            f.write(raw)
                        logging.info(f"Copied {data['fileName']}")
                    except Exception as e:
                        traceback.print_exc()

def main():
    global spl_DataID
    spl_DataID = int(open(SPL_V16_PATH + ".id", "r").read())
    print("Data ID Loaded: " + str(spl_DataID))

    print("Erasing previous data...")
    shutil.rmtree("content")
    shutil.rmtree("tasksheet")
    shutil.rmtree("cemusheet")
    os.mkdir("content")
    os.mkdir("tasksheet")
    os.mkdir("cemusheet")
    load_bossfiles()
    print("Generating fake schedules...")
    for region in SPL_REGION_LIST:
        for task in SPL_V16_TASKSHEET:
            tasksheet = make_fake_tasksheet(region, task)
            os.makedirs("tasksheet/1/" + region + "/", exist_ok=True)
            with open("tasksheet/1/" + region + "/" + task, "w") as f:
                f.write(tasksheet[0])
            
            os.makedirs("cemusheet/1/" + region + "/", exist_ok=True)
            with open("cemusheet/1/" + region + "/" + task, "w") as f:
                f.write(tasksheet[0].replace("10162c00", "10162b00"))

    copy_bossfiles()

if __name__ == "__main__":
    main()