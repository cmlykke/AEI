
/////////////////////////// instalaltion:

//////////////// install arimaa engine interface:
uv tool install aei

//this will install the following:
C:\Users\CMLyk\.local\bin

PS C:\Users\CMLyk> uv tool list
aei v1.4.0
- analyze
- gameroom
- postal_controller
- pyrimaa_tests
- roundrobin
- simple_engine
PS C:\Users\CMLyk> Get-Command analyze

CommandType     Name
-----------     ----
Application     analyze.exe


PS C:\Users\CMLyk> Get-Command gameroom

CommandType     Name
-----------     ----
Application     gameroom.exe


PS C:\Users\CMLyk> (Get-Command analyze).Source
C:\Users\CMLyk\.local\bin\analyze.exe

////////////////////// put sharp on path:
// get the sharp executable from the folder
arimaa-analyzer\ArimaaAnalyzer.Maui\Aiexecutables
//and the simple_engine from C:\Users\CMLyk\.local\bin
//create a folder for then (to be used with all AI's):
C:\Users\CMLyk\RiderProjects\arimaa-ai-location

//use this to verify the path:
(Get-Command simple_engine).Source

//use this to force windows to use the correct version of simple_engine:
C:\Users\CMLyk\RiderProjects\arimaa-ai-location\simple_engine.exe

/////////////////////////////////////////////// run the turnament
//assuming you have the  roundrobin.cfg file in C:\Users\CMLyk\RiderProjects\turnament

cd C:\Users\CMLyk\RiderProjects\turnament

roundrobin tournament.cfg





