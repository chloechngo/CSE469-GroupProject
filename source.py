#!/usr/bin/python
# CSE 469
# Group Project: Blockchain Chain of Custody
# Team Number: 3
import hashlib
import os
import struct
from datetime import datetime


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
    def __init__(self, prev_hash="", timestamp=0.0, case_id="", item_id=0, state=states['INITIAL'], data_length=0,
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
                           self.__case_id.encode('utf-8'),
                           self.__item_id,
                           self.__state,
                           self.__data_length,
                           self.__data.encode('utf-8'))


def init(blckch_file):
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


def add(blckch_file, case_id='', item_id=None):
    # Read the Blockchain file
    blckch = blckch_file.read()

    # Get the action time
    action_time = datetime.now().timestamp()

    ind = 0
    last_index = len(blckch)

    print(f"Case: {case_id}")

    current_hash = ''
    while ind < last_index:
        block_header = blckch[ind: ind + 76]
        prev_hash, timestamp, c_id, e_id, state, data_len = struct.unpack("32s d 16s I 12s I", block_header)

        # Check whether an item id already exists
        if item_id == e_id:
            print(f"Evidence item with item_id {item_id} already exists")
            exit(1)

        block_data = struct.unpack(str(data_len) + "s", blckch[ind + 76:ind + 76 + data_len])[0]
        block = block_header + block_data

        current_hash = hashlib.sha256(block)
        ind += len(block)

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
    print(f"Added item: {item_id}")
    print("\tStatus: CHECKEDIN")
    print(f"\tTime of action: {datetime.fromtimestamp(action_time)}")


if __name__ == "__main__":

    # Get the Blockchain File Path
    file_path = os.getenv("BCHOC_FILE_PATH")
    if file_path is None:
        file_path = os.path.join(os.getcwd(), "blockchain.bin")

    # Open the Blockchain File and Read the content
    with open(file_path, "rb+") as blockchain_file:
        # init(blockchain_file)
        add(blockchain_file, "65cc391d-6568-4dcc-a3f1-86a2f04140f3", 123456789)
