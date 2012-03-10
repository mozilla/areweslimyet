#!/usr/bin/env python

import os
import sys
import cgi
import json

form = cgi.FieldStorage()

def main():
  ret = { "result": "failure", "error": "Not implemented" }

  print("Content-Type: application/json; charset=utf-8\n\n")
  print(json.dumps(ret))

main()
