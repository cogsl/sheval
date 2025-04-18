#!/usr/bin/python
from enum import Enum
from src.shacl_runners import *

filename = "temp/positive_recursion_encoding1.ttl"
validation_report_file = "temp/positive_recursion_encoding_report.ttl"
validation_output = "temp/positive_recursion_encoding_output.ttl"
pyshacl = ["bin/pyshacl", "-o", "$validation_report_file", "--format", "turtle", "$filename" ]

shacl_tq = ["bin/shacl-1.4.4/bin/shaclvalidate.sh","-datafile", "$filename"]
jena_shacl = ["bin/apache-jena-5.3.0/bin/shacl", "v", "--data", "$filename"]


shaclex = ["shaclex","--validate","--engine","SHACLEX","--data", "$filename","--validationReportFormat","TURTLE","--showValidationReport","--validationReportFile", "$validation_report_file"]

command = mk_command(jena_shacl, filename, validation_output)
command_str = ' '.join(command) + " > " + validation_output
print(f"Command: {command_str}")
result = run(command, validation_output, 1)
print(f"Result of running command: {result}")
