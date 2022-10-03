# CSE 469
# Group Project: Blockchain Chain of Custody
# Team Number: 3
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
        return struct.pack("32s d 16s I 12s I",
                           self.__prev_hash.encode('utf-8'),
                           self.__timestamp,
                           self.__case_id.encode('utf-8'),
                           self.__item_id,
                           self.__state,
                           self.__data_length)


def init(blckch_file):
    # Read the BlockChain File
    blckch = blckch_file.read()

    # If the Initial Block does not exist
    if len(blckch) == 0:
        # Create the initial block
        timestamp = datetime.now().timestamp()
        state = struct.pack("12s", "INITIAL".encode('utf-8'))
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


if __name__ == "__main__":

    # Get the Blockchain File Path
    file_path = os.getenv("BCHOC_FILE_PATH")
    if file_path is None:
        file_path = os.path.join(os.getcwd(), "blockchain.bin")

    # Open the Blockchain File and Read the content
    with open(file_path, "rb+") as blockchain_file:
        init(blockchain_file)
