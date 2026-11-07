import sys
import secrets
from fastapi import FastAPI
import uvicorn
import threading


app = FastAPI()

mb_text = 30
mb_write = 1500

global_counter = 0

@app.get("/")
async def query():
    # add 1 to global_counter
    global global_counter
    global_counter+= 1
    return {"counter": global_counter}

def write_random_data(file, file2):
    # make this function run indefinitely writing random data to the file and flushing it to disk

    while True:
        # Generate random data
        random_data = secrets.token_urlsafe(2 * 1024 * 1024) # 1 MB is random
        random_data = random_data * int(mb_text/2)
        iter_num = mb_write // mb_text
        for i in range(iter_num):
            # Open the file in write mode
            with open(file, 'w') as f:
                # Write the data to the file
                f.write(random_data)
                # Flush the data to disk
                f.flush()
            # Open the file2 in write mode
            with open(file2, 'w') as f:
                # Write the data to the file
                f.write(random_data)
                # Flush the data to disk
                f.flush()
def run_server():
    uvicorn.run(app, host="10.0.8.3", port=23456, loop="asyncio")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <file1_path> <file2_path>")
        sys.exit(1)

    file = sys.argv[1]
    file2 = sys.argv[2]

    # start fastapi server in a separate thread
    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    # continue with the script
    try:
        write_random_data(file, file2)
    except KeyboardInterrupt:
        print("\nScript terminated by user.")