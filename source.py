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
        timestamp = datetime.now().timestamp()
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
    action_time = datetime.now().timestamp()

    index = 0
    last_index = len(blckch)

    print(index, last_index)
    case_id = uuid.UUID(case_id)

    # current_hash = ''.encode('utf-8')
    while index < last_index:

        block_header = blckch[index: index + 76]
        prev_hash, timestamp, c_id, e_id, state, data_len = struct.unpack("32s d 16s I 12s I", block_header)

        print(e_id, item_id)

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
    print(f"\tTime of action: {datetime.fromtimestamp(action_time)}")


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
    action_time = datetime.now().timestamp()

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
    print(f"\tTime of action: {datetime.fromtimestamp(action_time)}")


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
    action_time = datetime.now().timestamp()

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
    print(f"\tTime of action: {datetime.fromtimestamp(action_time)}")

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
    action_time = datetime.now().timestamp()

    index = 0
    last_index = len(blckch)
    
    exists_flag = False
    checkedin = False

    current_hash = ''
    case_id = ''

    #The item must be CHECKEDIN
    while index < last_index:
        block_header = blckch[index: index + 76]
        prev_hash, timestamp, c_id, e_id, state, data_len = struct.unpack("32s d 16s I 12s I", block_header)
        if item_id == e_id:
            
            if state != BlockChain.states['CHECKEDIN']:
                checkedin = False

            elif state == BlockChain.states['CHECKEDIN']:
                print("TRUE: index ", index)
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

    new_block = BlockChain(
        prev_hash=current_hash.hexdigest(),
        timestamp=action_time,
        case_id=case_id,
        item_id=item_id,
        state=BlockChain.states[reason]
    )
    new_block_bin = new_block.get_binary_data()

    blckch_file.seek(0, 2)
    blckch_file.write(new_block_bin)

	#Reason must be one of: DISPOSED, DESTROYED, or RELEASED. If the reason given is RELEASED, -o must also be given.
    if (reason == "DISPOSED") or (reason == "DESTROYED"):
        # Print the status message
        print(f"Case: {uuid.UUID(case_id.hex())}")
        print(f"Removed item: {item_id}")
        print(f"\tStatus: {reason}")
        print(f"\tTime of action: {datetime.fromtimestamp(action_time)}")
       
    elif reason == BlockChain.states['RELEASED']:
            # Print the status message
            print(f"Case: {uuid.UUID(case_id.hex())}")
            print(f"Removed item: {item_id}")
            print(f"\tStatus: {BlockChain.states['RELEASED']}")
            print(f"\tOwner info: {owner}")
            print(f"\tTime of action: {datetime.fromtimestamp(action_time)}")

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
		    #if the owner info isn't given
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
		
	    #calling the function
	    remove(blckch_file, item_id, reason, owner)

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
