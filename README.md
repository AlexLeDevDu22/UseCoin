premiere version de test

pour avoir un appercu:

- lancer 2 shells
  Shell 1:>>> python3 main.py prompter --port 5000 --peers 5001 #le shell qui va requester
  Shell 2:>>> python3 main.py miner --port 5001 --peers 5000 #le shell qui va miner, utilisant le LLM
