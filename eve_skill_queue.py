# MIT License

# Copyright (c) 2021 Jay Blunt

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import datetime
import simplejson as json
import requests
import cachecontrol
import requests_futures.sessions
import concurrent.futures

import pymprog


class EveSkillQueue(object):

    attribute_names = {
        164: "charisma",
        165: "intelligence",
        166: "memory",
        167: "perception",
        168: "willpower"
    }

    attribute_ids = sorted(attribute_names.keys())

    def total_skillqueue_minutes(self, skill_queue, attr_profile):
        sp_minutes = 0.0
        for s in skill_queue:
            s_id = s.get('skill_id')
            s_attr = self.skill_attributes.get(
                s_id, [0] * len(EveSkillQueue.attribute_ids))
            s_sp = int(s.get('level_end_sp', 0) -
                       s.get('training_start_sp', 0))
            assert(len(s_attr) == len(attr_profile))
            s_speed = sum([attr_profile[i] * s_attr[i]
                          for i in range(len(attr_profile))])
            # print("{}: {}".format(s_id, s_speed))
            sp_minutes += s_sp / s_speed
        return sp_minutes

    def _read_skillinfo(self, skill_ids):
        self.skill_attributes = dict()
        self.skill_names = dict()

        esi_universe_types = "https://esi.evetech.net/latest/universe/types/{}/"
        response_futures = [self.session.get(
            esi_universe_types.format(x)) for x in skill_ids]

        while len(response_futures) > 0:
            next_response_futures = list()
            for response in concurrent.futures.as_completed(response_futures):
                result = response.result()
                if result.status_code not in [200]:
                    next_response_futures.append(session.get(result.url))
                    continue

                payload = result.json()
                type_id = payload.get('type_id')
                if type_id == None:
                    continue

                attr = dict()
                for dogma_attr in payload.get('dogma_attributes', []):
                    attr_id = dogma_attr.get('attribute_id')
                    if attr_id not in [180, 181]:
                        continue

                    attr_value = int(dogma_attr.get('value', 0))
                    if attr_value not in EveSkillQueue.attribute_ids:
                        continue

                    if attr_id == 180:
                        attr[attr_value] = 1.0
                    elif attr_id == 181:
                        attr[attr_value] = 0.5

                self.skill_attributes[type_id] = list(
                    [attr.get(x, 0) for x in EveSkillQueue.attribute_ids])
                self.skill_names[type_id] = payload.get('name')

            response_futures = next_response_futures

    def _minimize_skillqueue(self, sp_queue, implant_level):

        attribute_sum = (20 + implant_level) * len(EveSkillQueue.attribute_ids)
        p = pymprog.model(self.__class__.__name__)
        p.verbose(False)
        x = p.var('x', len(EveSkillQueue.attribute_ids),
                  int, bounds=(5+implant_level, 35+implant_level))
        p.maximize(sum(sum(
            elem[i] * x[i] for i in range(len(EveSkillQueue.attribute_ids))) for elem in sp_queue))
        sum([x[i] for i in range(len(EveSkillQueue.attribute_ids))]
            ) == attribute_sum
        p.solver('intopt', msg_lev=pymprog.glpk.GLP_MSG_OFF)
        p.solve()

        opt_profile = [0] * len(EveSkillQueue.attribute_ids)
        if p.get_status() in [pymprog.glpk.GLP_OPT, pymprog.glpk.GLP_FEAS]:
            opt_profile = [
                int(x[i].primal)-implant_level for i in range(len(EveSkillQueue.attribute_ids))]
        p.end()

        return opt_profile

    def __init__(self, session):
        self.session = session
        self.skill_attributes = dict()
        self.skill_names = dict()

    def process_skillqueue(self, filename, implant_level):

        skill_queue = list()
        with open(filename) as ifp:
            skill_queue = json.load(ifp)

        skill_ids = list(filter(lambda x: x != None, [
                         x.get('skill_id') for x in skill_queue]))
        sp_total = sum([int(x.get('level_end_sp', 0) -
                       x.get('training_start_sp', 0)) for x in skill_queue])

        self._read_skillinfo(skill_ids)

        sp_queue = list()
        # sp_max_skillname_width = max(len(v) for v in self.skill_names.values())
        for s in skill_queue:
            s_id = s.get('skill_id')
            s_sp = float(s.get('level_end_sp', 0) -
                         s.get('training_start_sp', 0)) / float(sp_total)
            s_weights = list(map(lambda x: x * s_sp, self.skill_attributes.get(
                s_id, [0] * len(EveSkillQueue.attribute_ids))))
            # print("{:>{width}}: {}".format(self.skill_names.get(
            #     s_id, ''), s_weights, width=sp_max_skillname_width))
            sp_queue.append(s_weights)

        base_profile = [20] * len(EveSkillQueue.attribute_ids)
        base_profile_implants = list(
            map(lambda x: x+implant_level, base_profile))
        print(base_profile)
        print("{}".format({EveSkillQueue.attribute_names[EveSkillQueue.attribute_ids[i]]: base_profile[i] for i in range(
            len(EveSkillQueue.attribute_ids))}))
        print(datetime.timedelta(minutes=self.total_skillqueue_minutes(
            skill_queue, base_profile_implants)))

        opt_profile = self._minimize_skillqueue(sp_queue, implant_level)
        opt_profile_implants = list(
            map(lambda x: x+implant_level, opt_profile))
        print(opt_profile)
        print("{}".format({EveSkillQueue.attribute_names[EveSkillQueue.attribute_ids[i]]: opt_profile[i] for i in range(
            len(EveSkillQueue.attribute_ids))}))
        print(datetime.timedelta(minutes=self.total_skillqueue_minutes(
            skill_queue, opt_profile_implants)))

        return {EveSkillQueue.attribute_names[EveSkillQueue.attribute_ids[i]]: opt_profile[i] for i in range(len(EveSkillQueue.attribute_ids))}


parser = argparse.ArgumentParser()
parser.add_argument(
    "-i",
    "--implants",
    default=0,
    type=int,
    dest="implants",
    help="level of implants"
)
parser.add_argument("skillqueue")
args = parser.parse_args()


base_session = cachecontrol.CacheControl(requests.session())
session = requests_futures.sessions.FuturesSession(session=base_session)

opt = EveSkillQueue(session)
opt_attr = opt.process_skillqueue(args.skillqueue, args.implants)
print("{}".format(opt_attr))
