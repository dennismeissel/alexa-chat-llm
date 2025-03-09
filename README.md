# Alexa Chat LLM

Here's an example of how to configure Alexa to call a Large Language Model for each query.

You can deploy this skill in your private Alexa developer account, and it will be available on all of your Alexa devices.

This skill does not need to be published live to be used personally on your Alexa devices.

## Getting started

### Configure the Skill
- Create Alexa Skill in the developer console
- Set an Invocation Name
- In Interaction Model add an Intent with the name `llm_call`
- Add the Intent Slot `question` of type `AMAZON.SearchQuery` to the new Intent
- For the Slot `question`
  - Enable "Is this slot required to fulfill the intent"
  - Add an Alexa speech prompt, which will be pronounced every time, i.e. "Ask your question"
  - In the User utterances add just `{question}`
- Go back to the `llm_call` Intent
  - Add a Sample Utterance containing any word and `{question}`, i.e. `question {question}`. This is only required to pass validation; the actual logic is not used.
  - In Dialog Delegation Strategy set "disable auto delegation"
- Build the Skill and check for errors

### Add the code

- Open the "Code" tab and replace the content of `lambda_function.py` with the one from this repository.
- Create `.env` and fill the values according to `.env-example` in this repository
- Deploy the Skill

## Using the skill

After the deployment the skill will be available on all of the Alexa devices linked to the account.

To test it, you can say "Alexa, start {invocation name}". You can also do it in the tab "Test" of the developer console.
