
///////////// instalaltion:

* make sure python is installed

* clone the current AEI repo.

////////////// run round robin turnament between two .exe AI's:

Add the paths pf the two AI's to the config file.:
roundrobin_local.cfg

cd C:\Users\CMLyk\PycharmProjects\AEI

uv run python -m pyrimaa.roundrobin --config manual_testing\roundrobin_local.cfg

(depending on your python installation)

///////////// run round robin between a .exe bot in arimaa-ai-location folder
///////////// and an experimental bot in experimental_ai folder

cd C:\Users\CMLyk\PycharmProjects\AEI

uv run python -m pyrimaa.roundrobin --config manual_testing\experimental_local.cfg


