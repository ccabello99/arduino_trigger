from pyleco.directors.director import Director

class ArduinoDirector(Director):
    def __init__(self, actor: str, name:str, **kwargs):
        super().__init__(actor=actor, name=name, **kwargs)

    @property
    def device_port(self):
        return self.get_parameters(parameters=["device_port"])["device_port"]
    @property
    def pins(self):
        return self.get_parameters(parameters=["pins"])["pins"]
    
    def stop(self):
        response_id = self.call_action_async(action="stop")
        return response_id
    
    def sendPulse(self, pulse: str):
        response_id = self.call_action_async(action="sendPulse", pulse=pulse)
        return response_id # self.read_rpc_response(response_id) later to get the response
    
    def sendPulseSequence(self, sequence: str):
        response_id = self.call_action_async(action="sendPulseSequence", sequence=sequence)
        return response_id
    
    def updateCFile(self, CFilePath: str):
        response_id = self.call_action_async(action="updateCFile", CFilePath=CFilePath)
        return response_id