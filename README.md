Magic Doc Enhancer

# What is this tool for? 
The aim of this small program is to leverage OpenAI API to:
1. Help you improve or transform your document: 
   1. The tool can create a version of your document with a little improved formulation (from any language) allowing you to spot in a more productive fashion any area that was either unclear or needed improvement.
   2. The tool can as well improve heavily the formulation.
   3. An intermediate improvement is as well possible.
2. The tool can as well translate a document from any language to any other.
3. Because the tool is extensible, it allows you to perform any transformation of your choice creating a JSON file for the request.

# How shall I use this tool?
## Prerequisites
* You need to have git, python3 and pip3 installed.
* Run `pip install -r magic-document-enhancer/requirements.txt`
* Create an API Key (For OpenAI see  https://platform.openai.com/account/api-keys)
  * Depending on your OS, you can create the variable in 
    * Bash: `export OPENAI_API_KEY="sk-qxxxxxxxxxxxxxxxxxxxxxxxxxxxx"`
    * Windows PowerShell: `$env:OPENAI_API_KEY="sk-qxxxxxxxxxxxxxxxxxxxxxxxxxxxx"`
    * Windows CMD: `set OPENAI_API_KEY="sk-qxxxxxxxxxxxxxxxxxxxxxxxxxxxx"`

Using the same approach, you will have a set the variable agaonst the endpoint. Example for bash: `export OPENAI_BASE_URL="https://<my-end-point>"`

You are now ready to use the tool!

## Transforming a document

This is an example: 

```
cd magic-document-enhancer
python transform_document --from_document mydoc.docx --to_document mydoc-updated.docx
```
The tool exists currently only as a command line: `python transform_document -h` will provide you something like:
```bash
usage: usage: transform_document [-h] [--from_document FROM_DOCUMENT] [--to_document TO_DOCUMENT] [--transformation TRANSFORMATION] [--paragraph_start_min_word_numbers PARAGRAPH_START_MIN_WORD_NUMBERS]
                          [--paragraph_start_min_word_length PARAGRAPH_START_MIN_WORD_LENGTH] [--use_debugger_ai] [--debug] [--trace] [--max_number_threads MAX_NUMBER_THREADS] [--language LANGUAGE]
                          [--engine ENGINE]

options:
  -h, --help            show this help message and exit
  --from_document FROM_DOCUMENT
                        Specify the document to open
  --to_document TO_DOCUMENT
                        Specify the document to save
  --transformation TRANSFORMATION
                        Specify one transformation request to process from the following list: [[ 0: Improve document for technical stakeholders *** 1: Create document document for technical stakeholders *** 2: Improve document for sales and non technical stakeholders *** 3: Create document document for sales and non technical stakeholders *** 4: Translate document
  --paragraph_start_min_word_numbers PARAGRAPH_START_MIN_WORD_NUMBERS
                        When defining the start of a line or paragraph this defines the minimum number of words (1 per default)
  --paragraph_start_min_word_length PARAGRAPH_START_MIN_WORD_LENGTH
                        When defining the start of a line or paragraph this defines the minimum number of chars in each of the initial words (2 per default)
  --use_debugger_ai     Use a fake ML engine to debug application
  --debug               Set logging to debug
  --trace               Set logging to trace
  --max_number_threads MAX_NUMBER_THREADS
                        Specify the maximum number of parallel thread (Default 1)
  --language LANGUAGE   Specify the language of your text
  --engine ENGINE       Engine name.

```
## Extending the script with additional requests
See below an example of a request to be applied on the document to translate the document to french:
```json
[
      {
        "request_name": "Translate document to french", 
        "how_to_transform": [
          { 
            "role": "system", 
            "content": "You are a native french writer higly skilled to translate technical english text to french.\n"
          },
          { 
            "role": "user", 
            "content": 
                  "- Please translate the document to french making it very clear for deep technical people. Please enhance technical explanations or technical words ensuring the text can be shared with a large technical audience.\n - Provide NO explanation of any change you perform.\n - Provide NO comment regarding any change.\n - Do NOT modify the meaning of the text.\n - If you cannot translate then provide the same text.\n"
          }
        ],
       "temperature": 0.2, "top_p": 0.4 
      }
]
```
In order to ensure the script can take this request along with the default ones, you will need to referemnce the json file with an environment variable. Assuming the json file is in current directory and named `additional_requests.json`, you will need to define the variable `MAGIC_ADDITIONAL_REQUEST` as follows:

`export MAGIC_ADDITIONAL_REQUEST=$(pwd)/additional_requests.json`

Checking that the json file is properly taken into account happens extracting the help and checking transformations options:

```bash
usage: transform_document [-h] [--from_document FROM_DOCUMENT] [--to_document TO_DOCUMENT] [--transformation TRANSFORMATION] [--paragraph_start_min_word_numbers PARAGRAPH_START_MIN_WORD_NUMBERS]
                          [--paragraph_start_min_word_length PARAGRAPH_START_MIN_WORD_LENGTH] [--use_debugger_ai] [--debug] [--trace] [--max_number_threads MAX_NUMBER_THREADS] [--language LANGUAGE]
                          [--engine ENGINE]

options:
  -h, --help            show this help message and exit
  --from_document FROM_DOCUMENT
                        Specify the document to open
  --to_document TO_DOCUMENT
                        Specify the document to save
  --transformation TRANSFORMATION
                        Specify one transformation request to process from the following list: [[ 0: Improve document for technical stakeholders *** 1: Create document document for technical stakeholders ***
                        2: Improve document for sales and non technical stakeholders *** 3: Create document document for sales and non technical stakeholders *** 4: Translate document *** 5: Translate document to french ]]
  --paragraph_start_min_word_numbers PARAGRAPH_START_MIN_WORD_NUMBERS
                        When defining the start of a line or paragraph this defines the minimum number of words (1 per default)
  --paragraph_start_min_word_length PARAGRAPH_START_MIN_WORD_LENGTH
                        When defining the start of a line or paragraph this defines the minimum number of chars in each of the initial words (2 per default)
  --use_debugger_ai     Use a fake ML engine to debug application
  --debug               Set logging to debug
  --trace               Set logging to trace
  --max_number_threads MAX_NUMBER_THREADS
                        Specify the maximum number of parallel thread (Default 1)
  --language LANGUAGE   Specify the language of your text
  --engine ENGINE       Engine name.

```

# Technical details
## How it works
Word documents are transformed in a JSON structure like the following:
```json
     [{"Heading 1": [
         {"Heading name": "Heading ...", "Pointer": pointer}
         {"Text": "Full Text content below heading1", "Pointer": [pointer1, pointer2, ...]},
         {"Heading 2": [
             {"Heading name": "Heading ...", "Pointer": pointer}
             {"Text": "Full Text content below Heading 2", "Pointer": [pointer1, pointer2, ...]},
             {"Heading 3": [
               {"Heading name": "Heading ...", "Pointer": pointer}
               {"Text": "Full Text content below Heading 3", "Pointer": [pointer1, pointer2, ...]}
             ]},
             {"Heading 3": [
               {"Heading name": "Heading ...", "Pointer": pointer}
               {"Text": "Full Text content below Heading 3", "Pointer": [pointer1, pointer2, ...]},
              ]},
         ]}
      ]},
      {"Heading 1": [   // When appending search latest of each element until parent heading is found
         {"Heading name": "Heading ...", "Pointer": pointer}
         {"Text": "Full Text content below heading1", "Pointer": [pointer1, pointer2, ...]},
         {"Heading 2": [
             {"Heading name": "Heading ...", "Pointer": pointer}
             {"Text": "Full Text content below Heading 2", "Pointer": [pointer1, pointer2, ...]}]
         },
         {"Heading 2": [
             {"Heading name": "Heading ...", "Pointer": pointer}
             {"Text": "Full Text content below Heading 2", "Pointer": [pointer1, pointer2, ...]}
             {"Heading 3": [
               {"Heading name": "Heading ...", "Pointer": pointer}
               {"Text": "Full Text content below Heading 3", "Pointer": [pointer1, pointer2, ...]},
              ]}
           ]
         }
        ]
      }
     ]

```
When performing the request, the script tries to provide some contect to the LLM:
* For word documents, context is currently the list of headers happening before the text.
* For Powerpoint document the slide content is the context.

While transforming a Word or Powerpoint document the styles in the document often look very awkward and will require hands on changes. In order to improve this, the script will have to handle properly the stylings.

# Improvements required
Following is the list of improvements that this script will require:
1. Handling styles of the destination document
2. Work with KGPT team to ensure we are following properly the openai api: I was able to use openai endpoint with openai API however for some reasons that still need to be analyzed it required some workarounds when using KGPT endpoint.
3. Temperature and Top_p despite provided to thr API do not seem to influence the generated output.
4. Some refactoring is needed: Because I worked in my free time, I was not able to deliver the right level of quality.