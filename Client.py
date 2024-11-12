import socket
import sys
import threading

# Function to listen for incoming messages from the server
def listen_for_messages(sock):
    while True:
        try:
            # Receive and decode messages from the server
            data = sock.recv(1024).decode()
            if not data:
                print("Server closed the connection.")
                break
            print("\n" + data)  # Print message with a new line to avoid overlap with user input
        except Exception as e:
            print("Error receiving data:", e)
            break

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect the socket to the port where the server is listening
server_address = ('192.168.1.15', 10000)
print('Connecting to %s port %s' % server_address)
sock.connect(server_address)

try:
    # Receive the prompt from the server
    prompt = sock.recv(1024).decode()
    
    # Enter the name and send it to the server
    client_name = input(prompt)
    sock.sendall(client_name.encode())

    # Start a thread to listen for incoming messages from the server
    listener_thread = threading.Thread(target=listen_for_messages, args=(sock,))
    listener_thread.daemon = True  # Daemonize thread to end with the main program
    listener_thread.start()

    # Main loop to communicate with the server
    while True:
        # Input a message to send to the server
        message = input()
        if message.lower() == 'exit':
            print("Disconnecting from server.")
            break
        
        # Send the message to the server
        sock.sendall(message.encode())

finally:
    # Close the socket to clean up
    sock.close()
    print("Connection closed.")
