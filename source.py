#!/usr/bin/env python3
# CSE 469
# Group Project: Blockchain Chain of Custody
# Team Number: 3

import hashlib
import os
import struct
import sys
from datetime import datetime
import uuid
from pathlib import Path
import maya


class BlockChain:
    """
    BlockChain Structure:

    Member Variables:
        Offset 00 - Previous Hash - 32 byte string
        Offset 32 - Timestamp - 8 byte Regular UNIX timestamp
        Offset 40 - Case ID - 16 byte Integer
        Offset 56 - Item ID - 4 byte Integer
        Offset 60 - State - 12 byte string
        Offset 72 - Data Length - 4 byte Integer
        Offset 76 - Data - 0 to 2^32 bytes

    Member Methods:
        get_binary_data - Packs the members of a Blockchain object into binary
    """

    # Encoded Possible Block States
    states = {
        'INITIAL': struct.pack("12s", "INITIAL".encode('utf-8')),
        'CHECKEDIN': struct.pack("12s", "CHECKEDIN".encode('utf-8')),
        'CHECKEDOUT': struct.pack("12s", "CHECKEDOUT".encode('utf-8')),
        'DISPOSED': struct.pack("12s", "DISPOSED".encode('utf-8')),
        'DESTROYED': struct.pack("12s", "DESTROYED".encode('utf-8')),
        'RELEASED': struct.pack("12s", "RELEASED".encode('utf-8')),
    }

    # Constructor Function
    def __init__(self, prev_hash="", timestamp=0.0, case_id=b'', item_id=0, state=states['INITIAL'], data_length=0,
                 data=""):
        self.__prev_hash = prev_hash
        self.__timestamp = timestamp
        self.__case_id = case_id
        self.__item_id = item_id
        self.__state = state
        self.__data_length = data_length
        self.__data = data

    # Method to pack the member variables in Binary Format
    def get_binary_data(self):
        return struct.pack("32s d 16s I 12s I " + str(self.__data_length) + "s",
                           self.__prev_hash.encode('utf-8'),
                           self.__timestamp,
                           self.__case_id,
                           self.__item_id,
                           self.__state,
                           self.__data_length,
                           self.__data.encode('utf-8'))


def init(blckch_file):
    """
    :param blckch_file: the blockchain file pointer for reading and writing
    :return: 0 for success, 1 otherwise
    """
    # Read the BlockChain File
    blckch = blckch_file.read()

    # If the Initial Block does not exist
    if len(blckch) == 0:
        # Create the initial block
        timestamp = maya.now()._epoch
        state = BlockChain.states["INITIAL"]
        data_length = 14
        data = "Initial block"
        blckch_obj = BlockChain(timestamp=timestamp, state=state, data_length=data_length, data=data)

        # Write the block in the file
        blckch_file.write(blckch_obj.get_binary_data())

        # Print Status Message
        print("Blockchain file not found. Created INITIAL block.")

    # If the Initial Block already exists
    else:
        # Parse the initial block header
        initial_block = blckch[:76]
        # Retrieve the block state
        initial_block_state = initial_block[60:72]

        if initial_block_state == BlockChain.states["INITIAL"]:
            print("BlockChain file found with INITIAL block.")
        else:
            exit(1)  # Failure


def add(blckch_file, case_id, item_id):
    """
    :param blckch_file: the blockchain file pointer for reading, writing
    :param case_id: the case identifier that the evidence is associated with
    :param item_id: the evidence item’s identifier
    :return: 0, if the evidence is successfully added, 1 otherwise
    """

    # Read the Blockchain file
    blckch = blckch_file.read()

    # Get the action time
    action_time = maya.now()._epoch

    index = 0
    last_index = len(blckch)

    case_id = uuid.UUID(case_id)

    # current_hash = ''.encode('utf-8')
    while index < last_index:

        block_header = blckch[index: index + 76]
        prev_hash, timestamp, c_id, e_id, state, data_len = struct.unpack("32s d 16s I 12s I", block_header)

        # Check whether an item id already exists
        if item_id == e_id:
            print(f"Evidence item with item_id {item_id} already exists")
            exit(1)

        block_data = struct.unpack(str(data_len) + "s", blckch[index + 76:index + 76 + data_len])[0]
        block = block_header + block_data

        # current_hash = block
        index += len(block)

    new_block = BlockChain(
        # prev_hash=hashlib.sha256(current_hash).hexdigest(),
        timestamp=action_time,
        case_id=case_id.bytes[::-1],  # To convert it to Little Endian
        item_id=item_id,
        state=BlockChain.states['CHECKEDIN']
    )
    new_block_bin = new_block.get_binary_data()

    blckch_file.seek(0, 2)
    blckch_file.write(new_block_bin)

    # Print the status message
    print(f"Added item: {item_id}")
    print("\tStatus: CHECKEDIN")
    print(f"\tTime of action: {maya.parse(datetime.fromtimestamp(action_time)).iso8601()}")


def checkout(blckch_file, item_id):
    """
    :param blckch_file: the blockchain file pointer for reading, writing
    :param item_id: the evidence item’s identifier
    :return: 0, if the evidence is successfully checkedout,
                1, if the evidence is not checked in, checkout cannot be performed
                2, if the evidence does not exist
    """

    # Read the Blockchain file
    blckch = blckch_file.read()

    # Get the action time
    action_time = maya.now()._epoch

    index = 0
    last_index = len(blckch)

    exists_flag = False
    checkedin = False

    current_hash = ''
    case_id = ''

    while index < last_index:
        block_header = blckch[index: index + 76]
        prev_hash, timestamp, c_id, e_id, state, data_len = struct.unpack("32s d 16s I 12s I", block_header)

        if item_id == e_id:
            if state != BlockChain.states['CHECKEDIN']:
                checkedin = False

            elif state == BlockChain.states['CHECKEDIN']:
                checkedin = True
                exists_flag = True
                case_id = c_id

        block_data = struct.unpack(str(data_len) + "s", blckch[index + 76:index + 76 + data_len])[0]
        block = block_header + block_data

        current_hash = hashlib.sha256(block)
        index += len(block)

    if not exists_flag:
        print("Error: No matching item")
        exit(2)

    if not checkedin:
        print("Error: Cannot check out a checked out item. Must check it in first.")
        exit(1)

    new_block = BlockChain(
        prev_hash=current_hash.hexdigest(),
        timestamp=action_time,
        case_id=case_id,
        item_id=item_id,
        state=BlockChain.states['CHECKEDOUT']
    )
    new_block_bin = new_block.get_binary_data()

    blckch_file.seek(0, 2)
    blckch_file.write(new_block_bin)

    # Print the status message
    print(f"Case: {uuid.UUID(case_id.hex())}")
    print(f"Checked out item: {item_id}")
    print("\tStatus: CHECKEDOUT")
    print(f"\tTime of action: {maya.parse(datetime.fromtimestamp(action_time)).iso8601()}")


def checkin(blckch_file, item_id):
    """
    :param blckch_file: the blockchain file pointer for reading, writing
    :param item_id: the evidence item’s identifier
    :return: 0, if the evidence is successfully checkedin,
                1, if the evidence does not exist
    """

    # Read the Blockchain file
    blckch = blckch_file.read()

    # Get the action time
    action_time = maya.now()._epoch

    index = 0
    last_index = len(blckch)

    exists_flag = False

    current_hash = ''
    case_id = ''

    while index < last_index:
        block_header = blckch[index: index + 76]
        prev_hash, timestamp, c_id, e_id, state, data_len = struct.unpack("32s d 16s I 12s I", block_header)

        if item_id == e_id:
            if state == BlockChain.states['CHECKEDOUT']:
                exists_flag = True
                case_id = c_id
            else:
                exists_flag = False

        block_data = struct.unpack(str(data_len) + "s", blckch[index + 76:index + 76 + data_len])[0]
        block = block_header + block_data

        current_hash = hashlib.sha256(block)
        index += len(block)

    if not exists_flag:
        print("Error: No matching item")
        exit(1)

    new_block = BlockChain(
        prev_hash=current_hash.hexdigest(),
        timestamp=action_time,
        case_id=case_id,
        item_id=item_id,
        state=BlockChain.states['CHECKEDIN']
    )
    new_block_bin = new_block.get_binary_data()

    blckch_file.seek(0, 2)
    blckch_file.write(new_block_bin)

    # Print the status message
    print(f"Case: {uuid.UUID(case_id.hex())}")
    print(f"Checked in item: {item_id}")
    print("\tStatus: CHECKEDIN")
    print(f"\tTime of action: {maya.parse(datetime.fromtimestamp(action_time)).iso8601()}")


def remove(blckch_file, item_id, reason, owner):
    """
    :param blckch_file: the blockchain file pointer for reading, writing
    :param item_id: the evidence item’s identifier
    :param owner: info about the lawful owner
    :return: 0, if the evidence is successfully removed,
                1, if the evidence is not checked in, remove cannot be performed
                2, if the evidence does not exist
                3, if owner info is not given
    """

    # Read the Blockchain file
    blckch = blckch_file.read()

    # Get the action time
    action_time = maya.now()._epoch

    index = 0
    last_index = len(blckch)

    exists_flag = False
    checkedin = False

    current_hash = ''
    case_id = ''

    # The item must be CHECKEDIN
    while index < last_index:
        block_header = blckch[index: index + 76]
        prev_hash, timestamp, c_id, e_id, state, data_len = struct.unpack("32s d 16s I 12s I", block_header)
        if item_id == e_id:

            if state != BlockChain.states['CHECKEDIN']:
                checkedin = False

            elif state == BlockChain.states['CHECKEDIN']:
                checkedin = True
                exists_flag = True
                case_id = c_id

        block_data = struct.unpack(str(data_len) + "s", blckch[index + 76:index + 76 + data_len])[0]
        block = block_header + block_data

        current_hash = hashlib.sha256(block)
        index += len(block)

    if not exists_flag:
        print("Error: No matching item")
        exit(2)

    if not checkedin:
        print("Error: Cannot remove an item. Must check it in first.")
        exit(1)

    # initialize new_block
    new_block = BlockChain(timestamp=action_time, case_id=case_id, item_id=item_id, state=BlockChain.states[reason],
                           data_length=0, data='')

    # Reason must be one of: DISPOSED, DESTROYED, or RELEASED. If the reason given is RELEASED, -o must also be given.
    if (reason == "DISPOSED") or (reason == "DESTROYED"):
        new_block = BlockChain(
            timestamp=action_time,
            case_id=case_id,
            item_id=item_id,
            state=BlockChain.states[reason],
            data_length=len(owner),
            data=owner.rstrip('\x00')
        )

        # Print the status message
        print(f"Case: {uuid.UUID(case_id.hex())}")
        print(f"Removed item: {item_id}")
        print(f"\tStatus: {reason}")
        print(f"\tTime of action: {maya.parse(datetime.fromtimestamp(action_time)).iso8601()}")

    elif reason == "RELEASED":
        new_block = BlockChain(
            timestamp=action_time,
            case_id=case_id,
            item_id=item_id,
            state=BlockChain.states[reason],
            data_length=len(owner) + 1,
            data=owner
        )
        # Print the status message
        print(f"Case: {uuid.UUID(case_id.hex())}")
        print(f"Removed item: {item_id}")
        print(f"\tStatus: {BlockChain.states['RELEASED']}")
        print(f"\tOwner info: {owner}")
        print(f"\tTime of action: {maya.parse(datetime.fromtimestamp(action_time)).iso8601()}")

    else:
        new_block = BlockChain(
            timestamp=action_time,
            case_id=case_id,
            item_id=item_id,
            state=struct.pack("12s", reason.encode('utf-8')),
        )

        # Print the status message
        print(f"Case: {uuid.UUID(case_id.hex())}")
        print(f"Removed item: {item_id}")
        print(f"\tStatus: {reason}")
        print(f"\tTime of action: {maya.parse(datetime.fromtimestamp(action_time)).iso8601()}")

    new_block_bin = new_block.get_binary_data()
    blckch_file.seek(0, 2)
    blckch_file.write(new_block_bin)


def verify(blckch_file):
    """
    Parse the blockchain and validate all entries
    :param blckch_file: the blockchain file
    :return:
    """

    # Read the Blockchain file
    blckch = blckch_file.read()

    index = 0
    last_index = len(blckch)

    numBlocks = 0

    evidenceStates = {}
    hashValues = []

    while index < last_index:

        numBlocks += 1

        block_header = blckch[index: index + 76]

        # Invalid Block
        if len(block_header) != 76:
            print("Error: Bad Block")
            exit(1)

        prev_hash, timestamp, c_id, e_id, state, data_len = struct.unpack("32s d 16s I 12s I", block_header)

        # Missing Initial Block
        if numBlocks == 1 and state != BlockChain.states["INITIAL"]:
            print("Error: Invalid Initial Block")
            exit(1)

        # Bad State
        if state not in BlockChain.states.values():
            print("Error: Bad State")
            exit(1)

        # Duplicate Parent Block
        if prev_hash in hashValues:
            print("Error: Duplicate Parent Block")
            exit(1)
        else:
            hashValues.append(prev_hash)

        # Maintaining the states
        if e_id not in evidenceStates.keys():
            evidenceStates[e_id] = state
        else:
            last_state = evidenceStates[e_id]

            # Double Checkin Check
            if last_state == BlockChain.states["CHECKEDIN"]:
                if state == BlockChain.states["CHECKEDIN"]:
                    print("Error: Double Checkin")
                    exit(1)
                else:
                    evidenceStates[e_id] = state

            # Double Checkout Check
            if last_state == BlockChain.states["CHECKEDOUT"]:
                if state == BlockChain.states["CHECKEDOUT"]:
                    print("Error: Double Checkout")
                    exit(1)
                else:
                    evidenceStates[e_id] = state

            # Operation after Remove
            if last_state == BlockChain.states["DISPOSED"] or last_state == BlockChain.states["DESTROYED"] \
                    or last_state == BlockChain.states["RELEASED"]:
                if state == BlockChain.states["CHECKEDIN"]:
                    print("Error: Checkin After Remove")
                    exit(1)
                elif state == BlockChain.states["CHECKEDOUT"]:
                    print("Error: Checkout After Remove")
                    exit(1)
                else:
                    print("Error: Double Remove")
                    exit(1)

        # Release without owner
        if state == BlockChain.states["RELEASED"]:
            if data_len == 0:
                print("Error: Release with No Owner")
                exit(1)

        block_data = struct.unpack(str(data_len) + "s", blckch[index + 76:index + 76 + data_len])[0]
        block = block_header + block_data

        last_hash = struct.pack("32s", hashlib.sha256(block).hexdigest().encode('utf-8'))

        # current_hash = block
        index += len(block)

    # Print the status message
    print(f"Transactions in blockchain: {numBlocks}")
    print("State of blockchain: CLEAN")


def log(blckch_file, case_id='', item_id=-1, reverse=False, num_entries=-1):
    """

    :param blckch_file: the blockchain file for reading purpose
    :param case_id: the optional case id
    :param item_id: the optional item id
    :param reverse: the reverse flag, if true the records will be printed end to beginning
    :param num_entries: optional number of entries
    :return:
    """

    def printBlock(blck):
        """
        A function to print the log entry
        :param blck: {timestamp, case_id, item_id, state}
        """
        time, case, item, action = blck

        print(f"Case: {uuid.UUID(case[::-1].hex())}")
        print(f"Item: {item}")
        print(f"Action: {list(BlockChain.states.keys())[list(BlockChain.states.values()).index(action)]}")
        print(f"Time: {maya.parse(datetime.fromtimestamp(time)).iso8601()}")
        print()

    # Read the Blockchain file
    blckch = blckch_file.read()

    index = 0
    last_index = len(blckch)

    blocks = []

    while index < last_index:
        block_header = blckch[index: index + 76]
        prev_hash, timestamp, c_id, e_id, state, data_len = struct.unpack("32s d 16s I 12s I", block_header)

        # If neither Case ID nor Item ID is given
        if case_id == '' and item_id == -1:
            blocks.append((timestamp, c_id, e_id, state))

        # If Case ID is not given, but Item ID is given
        elif case_id == '':

            # If Item ID matches with the current item id, or Item ID is not given
            if e_id == item_id or item_id == -1:
                blocks.append((timestamp, c_id, e_id, state))

        # If both Case ID, Item ID are given
        else:
            # If Case ID matches current case id
            if uuid.UUID(case_id).bytes[::-1] == c_id:

                # If Item ID matches with the current item id, or Item ID is not given
                if e_id == item_id or item_id == -1:
                    blocks.append((timestamp, c_id, e_id, state))

        block_data = struct.unpack(str(data_len) + "s", blckch[index + 76:index + 76 + data_len])[0]
        block = block_header + block_data

        index += len(block)

    # If reverse flag is True
    if reverse:
        blocks.reverse()

    # If num_entries not provided
    if num_entries == -1:
        num_entries = len(blocks)

    index = 0

    # Print the log entries
    while index < num_entries and index < len(blocks):
        printBlock(blocks[index])
        index += 1


def parse(arg, blckch_file):
    """
    Function to parse the input provided in the command line, and make function calls
    :param arg: the command line input
    :param blckch_file: the blockchain file
    """
    cmd = arg[0].lower()
    params = arg[1:]

    if cmd == "init":
        # init with additional parameters must cause error
        if len(params) > 0:
            exit(1)
        init(blckch_file)

    elif cmd == "add":
        case_id = params[1]

        # if there is either/both the case id or/and at least one item id is mission
        if len(params) < 4:
            exit(1)

        # Perform init to check whether add was called before init
        init(blckch_file)

        # Bring the file pointer to the beginning
        blckch_file.seek(0)

        print(f"Case: {case_id}")

        for index in range(3, len(params), 2):
            item_id = int(params[index])
            add(blckch_file, case_id, item_id)

    elif cmd == "checkout":
        item_id = int(params[-1])
        checkout(blckch_file, item_id)

    elif cmd == "checkin":
        item_id = int(params[-1])
        checkin(blckch_file, item_id)

    elif cmd == "remove":
        item_id = int(params[1])
        reason = params[3]
        owner = ''

        if reason == "RELEASED":
            # if the owner info isn't given
            if len(params) == 4:
                print("ERROR: Owner info is not given")
                exit(1)
            else:
                owner = params[-1]
        elif reason == "DESTROYED" or reason == "DISPOSED":
            owner = ''
        else:
            print("ERROR: Invalid reason")
            exit(1)

        # calling the function
        remove(blckch_file, item_id, reason, owner)

    elif cmd == "verify":
        verify(blckch_file)

    elif cmd == "log":
        num_entries = -1
        case_id = ''
        item_id = -1
        reverse = False

        for index in range(len(params)):
            if params[index] == "-r" or params[index] == "--reverse":
                reverse = True
            elif params[index] == "-n":
                num_entries = int(params[index + 1])
            elif params[index] == "-c":
                case_id = params[index + 1]
            elif params[index] == "-i":
                item_id = int(params[index + 1])

        log(blckch_file, case_id, item_id, reverse, num_entries)


if __name__ == "__main__":

    # Get the Blockchain File Path
    file_path = os.getenv("BCHOC_FILE_PATH")
    if file_path is None:
        file_path = os.path.join(os.getcwd(), "blockchain.bin")

    # Create the blockchain file if it doesn't exist
    Path(file_path).touch(exist_ok=True)

    # Open the Blockchain File and Read the content
    with open(file_path, "rb+") as blockchain_file:
        parse(sys.argv[1:], blockchain_file)

    # Close the Blockchain File
    blockchain_file.close()
