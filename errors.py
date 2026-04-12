class AppError(Exception):
    status = 500
    message = "Internal Server Error"

class BadRequest(AppError):
    status = 400
    message = "Bad Request"

class Forbidden(AppError):                                                                                                            
    status = 403                                                                                                                      
    message = "Forbidden"                                                                                                             
                                                                                                                                        
                                                                                                                                        
class NotFound(AppError):                                                                                                             
    status = 404                                                                                                                      
    message = "Not Found" 