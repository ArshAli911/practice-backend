import socket                                                                                                                             
                                                                                                                                            
HOST = "127.0.0.1"                                                                                                                        
PORT = 8080                                                                                                                               
                                                                                                                                            
request = (                                                                                                                               
      "GET / HTTP/1.1\r\n"                                                                                                                  
      f"Host: {HOST}:{PORT}\r\n"                                                                                                            
      "Connection: close\r\n"                                                                                                               
      "\r\n"                                                                                                                                
  )                                                                                                                                         
                                                                                                                                            
client_socket = socket.socket()                                                                                                           
client_socket.connect((HOST, PORT))                                                                                                       
client_socket.sendall(request.encode("utf-8"))                                                                                            
                                                                                                                                          
response = b""                                                                                                                            
while True:                                                                                                                               
    chunk = client_socket.recv(4096)                                                                                                      
    if not chunk:                                                                                                                         
        break                                                                                                                             
    response += chunk                                                                                                                     
                                                                                                                                          
print(response.decode("utf-8", errors="replace"))                                                                                         
client_socket.close()                                                                                                                     
                            