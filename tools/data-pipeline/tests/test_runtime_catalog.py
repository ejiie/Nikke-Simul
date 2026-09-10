import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_runtime import skill_roots, graph_closure, gauge_constants, burst_connection
import copy


class RuntimeCatalogTests(unittest.TestCase):
    def test_phases_are_not_lost_or_reordered(self):
        level = {'function_ids': [1], 'function_phases': {'after_hurt': [5], 'before_use': [2], 'after_use': [4], 'before_hurt': [3]}}
        self.assertEqual(skill_roots(level), [1,2,3,4,5])
        self.assertEqual(level['function_phases']['after_hurt'], [5])

    def test_nested_character_skill_and_cycles_preserve_closure(self):
        chains = {'functions': {'1': {'function_type':72,'function_value':9,'connected_function':[2]},
                               '2': {'function_type':1,'connected_function':[1]}, '3': {'function_type':1}},
                  'character_skills': {'9': {'function_phases': {'after_hurt':[3]}}}}
        functions, skills, missing = graph_closure(chains, [1])
        self.assertEqual(set(functions), {'1','2','3'})
        self.assertEqual(set(skills), {'9'})
        self.assertEqual(missing, [])

    def test_missing_edges_are_reported(self):
        chains = {'functions': {'1': {'function_type':72,'function_value':9,'connected_function':[2]}}}
        self.assertEqual(graph_closure(chains, [1])[2], ['character_skill:9','function:2'])

    def test_unreviewed_phase_cannot_silently_disappear(self):
        with self.assertRaises(ValueError):
            skill_roots({'function_phases': {'new_phase': [1]}})

    def test_gauge_source_mismatch_is_rejected_not_replaced_with_a_default(self):
        table={'burst_energy_max':100, 'ally':dict(per_sec=1,use_skill=2,skill_hit=3,shot_hit=4,
            hurt=5,cover_hurt=0,empty_ammo=6,kill=dict(minion=7,elite=8,centurion=9,boss=10))}
        config=dict(burst_energy_max='100',ulti_gauge_sec='1',ulti_gauge_use_skill='2',ulti_gauge_skill_hit='3',
            ulti_gauge_shot_hit='4',ulti_gauge_hurt='5',ulti_gauge_cover_hurt='0',ulti_gauge_empty_ammo='6',
            ulti_gauge_kill_m='7',ulti_gauge_kill_e='8',ulti_gauge_kill_c='9',ulti_gauge_kill_b='10')
        result=gauge_constants(table,config)
        self.assertEqual(result['capacityRaw'],100)
        self.assertEqual(result['formulaStatus'],'unverified')
        config['ulti_gauge_shot_hit']='99'
        with self.assertRaises(ValueError): gauge_constants(table,config)
        del config['ulti_gauge_shot_hit']
        with self.assertRaises(KeyError): gauge_constants(table,config)

    def test_burst_metadata_preserves_total_duration_and_reports_unresolved_replacement(self):
        character=dict(use_burst_skill=3,change_burst_step=4,burst_apply_delay=1,burst_duration=1500,shot_id=10,
            skills={'burst':{'levels':{'1':{'skill':{'skill_type':7,'skill_value_data':[
                {'skill_value':100},{'skill_value':4200},{'skill_value':11}]}}}}})
        weapon={'burst':dict(useBurstSkill='Step3',changeBurstStep='StepFull',applyDelaySec=.01,durationSec=15,
            energyPerShot=500,targetEnergyPerShot=1000,fullChargeEnergy=0)}
        role=dict(use_burst_skill='Step3',change_burst_step='StepFull',burst_apply_delay=1,burst_duration=1500,
            shot=dict(burst_energy_pershot=500,target_burst_energy_pershot=1000,full_charge_burst_energy=0))
        result=burst_connection(character,weapon,role)
        self.assertEqual(result['fullBurstDurationCs'],1500)
        self.assertEqual(result['unresolvedReplacementShotIds'],[11])
        for key,value in [('use_burst_skill','Step2'),('burst_duration',1000),('burst_apply_delay',28)]:
            bad=copy.deepcopy(role);bad[key]=value
            with self.assertRaises(ValueError): burst_connection(character,weapon,bad)
        bad=copy.deepcopy(role);bad['shot']['target_burst_energy_pershot']=1
        with self.assertRaises(ValueError): burst_connection(character,weapon,bad)
