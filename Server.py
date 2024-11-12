import socket
import threading
import time
from QuizQuestions import questions_set
import select


active_connections = {}
client_names = {}
scores = {}  # Dictionary to store scores for each client
lock = threading.Lock()
question_answered = threading.Event()  # Event to signal that the question was answered

# Function to handle client connections
def handle_client(connection, client_address):
    # Prompt client for their name
    while True:
        connection.sendall(b"Please enter your name: ")
        client_name = connection.recv(1024).decode().strip()

        # If the name is already taken, ask for a new one
        if client_name in client_names.values():
            connection.sendall(b"Name already taken. Please choose another name.\n")
        else:
            connection.sendall(b"Please hang on until we find other players: ")
            break

    # Register the connection and client name
    with lock:
        active_connections[client_address] = connection
        client_names[client_address] = client_name
        scores[client_address] = 0  # Initialize score for the client


    notices = f"Connection from {client_name} at {client_address}. Total connections: {len(active_connections)}\n"
    if len(active_connections) < 3:
        notices += f"{3 - len(active_connections)} more users are needed to start\n"
        broadcast(notices, sender_address=client_address)
        print(notices)
    else:
        print(notices)
        start_countdown(True)

        # quiz start
        try:
            print("Game has started!")
            round_number = 1
            for i, (question_text, correct_answer) in enumerate(questions_set):
                if i % 4 == 0 and i != 0:
                    broadcast(f"Round {round_number} is over!")
                    broadcast_scores()
                    round_number += 1

                broadcast(f"Question NBR {i + 1}: {question_text}")

                question_answered.clear()
                timer_thread = threading.Thread(target=start_countdown, args=(False, 15))
                timer_thread.start()

                # Listen for answers from all clients
                while not question_answered.is_set():
                    try:
                        # Use select to wait for incoming data on any client socket with a timeout
                        ready_sockets, _, _ = select.select(active_connections.values(), [], [], 1)
                        for connection in ready_sockets:
                            data = connection.recv(1024).decode().strip()
                            print(data)
                            client_address = next(addr for addr, conn in active_connections.items() if conn == connection)
                            client_name = client_names[client_address]

                            # Check if the answer is correct
                            if data:
                                if data.lower() == correct_answer.lower():
                                    broadcast(f"{client_name} answered correctly: {correct_answer}")
                                    scores[client_address] += 1
                                    question_answered.set()
                                    break
                                else:
                                    connection.sendall(b"Incorrect\n")
                    except Exception as e:
                        print(f"Error handling answer: {e}")

                # Wait for the timer to finish before moving to the next question
                timer_thread.join()
                
                # Announce the correct answer if time ran out
                if not question_answered.is_set():
                    broadcast(f"Time's up! The correct answer was: {correct_answer}")
                    question_answered.set()
                
                broadcast(f" The correct answer was: {correct_answer} Moving to the next question...\n ")


        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            with lock:
                del active_connections[client_address]
                del client_names[client_address]
                del scores[client_address]  # Remove score entry when client disconnects
            connection.close()
            print(f"Connection with {client_name} at {client_address} closed. Total connections: {len(active_connections)}")
            broadcast(f"{client_name} has left the chat.\n", sender_address=client_address)

# Function to broadcast a message to all clients except the sender
def broadcast(message, sender_address=None):
    with lock:
        for client_address, connection in active_connections.items():
            if client_address != sender_address:
                try:
                    connection.sendall(message.encode())
                except Exception as e:
                    print(f"Failed to send message to {client_address}: {e}")
def broadcast_scores():
    score_message = "Current Scores:\n"
    with lock:
        for client_address, score in scores.items():
            client_name = client_names[client_address]
            score_message += f"{client_name}: {score} points\n"
    broadcast(score_message)

# Countdown function with optional game start or question timer
def start_countdown(gameStarting, counter=3):
    for i in range(counter, 0, -1):
        if question_answered.is_set():
            return
        message = f"{i} seconds left...\n" if not gameStarting else f"Starting in {i} seconds...\n"
        if(i%3==0):
            broadcast(message)

        time.sleep(1)

    if not question_answered.is_set() and not gameStarting:
        broadcast("Time's up!\n")
        question_answered.set()

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('192.168.1.15', 10000)
    print(f"Starting up on {server_address[0]} port {server_address[1]}")
    sock.bind(server_address)
    sock.listen(5)
    print("Waiting for incoming connections...")

    while True:
        connection, client_address = sock.accept()
        client_thread = threading.Thread(target=handle_client, args=(connection, client_address))
        client_thread.daemon = True
        client_thread.start()

if __name__ == "__main__":
    main()
