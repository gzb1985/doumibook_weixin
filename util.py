import os

deployed_on_sae = False

if 'SERVER_SOFTWARE' in os.environ:
	deployed_on_sae = True
