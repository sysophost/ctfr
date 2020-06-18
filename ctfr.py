import re
import requests
import argparse
import time
from multiprocessing import Pool

PARSER = argparse.ArgumentParser()
PARSER.add_argument('-domain', '-d', type=str, action='append', required=True, help="Target domain.")
PARSER.add_argument('-output', '-o', type=str, help="Output file.")
PARSER.add_argument('-threads', '-t', type=int, default=5, help="Number of threads")
PARSER.add_argument('-verbose', '-v', action="store_true", help='Enable verbose output')
ARGS = PARSER.parse_args()

MAX_RETRY = 5
SLEEP_SECONDS = 3

verbose_print = print if ARGS.verbose else lambda *a, **k: None

def search_domain(domain):
	subdomains = []
	verbose_print(f"[i] Checking {domain}")

	retry_count = 0
	while ((resp := submit_query(domain)).status_code) == 429 and retry_count < MAX_RETRY:
		verbose_print(f"[i] Got HTTP 429 for {domain}, sleeping for {SLEEP_SECONDS} seconds")
		retry_count += 1
		time.sleep(SLEEP_SECONDS) 

	if retry_count == 5:
		print(f"[!] Exceeded retry count for {domain}, skipping")
		exit(1)

	if resp.status_code != 200:
		print(f"[!] Information not available for {domain}, received {resp.status_code} response code")
		exit(1)

	for (key, value) in enumerate(resp.json()):
		subdomains.append(value['name_value'])

	subdomains = sorted(set(subdomains))
	verbose_print(f"[i] Finished {domain}")
	return subdomains

def submit_query(domain):
	resp = requests.get(f"https://crt.sh/?q=%.{domain}&output=json")
	return resp

def save_subdomains(subdomain,output_file):
	with open(output_file, "a") as f:
		f.write(subdomain + '\n')
		f.close()

if __name__ == '__main__':
	# On OSX you may need to set the following env var to stop warnings about threading
	# export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
	pool = Pool(processes=ARGS.threads)
	search_results = pool.imap_unordered(search_domain, ARGS.domain)
	pool.close()
	for result in search_results:
		if result:
			for subdomain in result:
				print(f"{subdomain}")
				output = ARGS.output
				if output is not None:
					save_subdomains(subdomain, output)
			pool.terminate()
			break
	pool.join()