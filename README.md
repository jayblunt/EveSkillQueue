# EveSkillQueue

[python](https://www.python.org) script to estimate optimal [Eve Online](https://www.eveonline.com/) settings for a given skillqueue.

This uses a [GLPK](https://www.gnu.org/software/glpk/) wrapper to maximize the learning rate of a skill queue, with each item in the skill queue weighted by how many skill points are needed to complete the item.

## Setup your python environment

You will need python3 (3.8 or better) installed. To make your environment use the following commands:

```shell
$ python3 -m venv python-env
$ . python-env/bin/activate
$ pip install -U pip setuptools wheel
$ pip install -r requirements.txt
$ rehash
```

(```rehash``` is there in case you are using a shell that does not rehash search paths regularly. Looking at you, ```/bin/zsh``` on macOS)

## Example usage

There is an example skillqueue.json in the tree.

```shell
$ python eve_skill_queue.py -i 5 example_skillqueue.json
```

## Downloading your character's skill queue

The easiest way to download your eve character's skillqueue is to use the [EVE Swagger Interface](https://esi.evetech.net/ui/#/operations/Skills/get_characters_character_id_skillqueue). Use the "Authorize" button top-right of this page to login. Be sure to include the ```esi-skills.read_skillqueue.v1``` scope. One you have logged in use the "Try it out" option under the expanded /characters/{character_id}/skillqueue/ section. You will need to know your character's character_id - if you aren't sure, look at your character on [zkillboard](https://www.zkillboard.com) and use the number that is the last part of the url.

## Notes

Remember that you can only remap your skill attribtues once a year. Please don't even consider remapping your skill attributes until you are comfortable with this.

I chose a floor of 5 and a ceiling of 35 for the possible skill attributes - not sure if this is right.

The solution is *very* sensitive to changes in the input bounds. This suggests that I may not have setup the problem correctly, or that this is not the best approach.
