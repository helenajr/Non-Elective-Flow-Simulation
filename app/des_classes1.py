
import simpy
import pandas as pd
from sim_tools.distributions import (Exponential, Lognormal, Uniform)

class g: # global
    ed_inter_visit = 37.7 # see observed_edintervist notebook
    sdec_inter_visit = 128.8 # see sdec intervisit notebook
    other_inter_visit = 375.7 # see other intervisit notebook.
    number_of_nelbeds = 434 # see number beds notebook
    mean_time_in_bed = 13500 # see mean los notebook
    sd_time_in_bed = 24297
    sim_duration = 86400 #run for 60 days
    warm_up_period = 86400 # warm up for 60 days - need to test if  this is long enough
    number_of_runs = 10

class Patient:
    def __init__(self, p_id):
        self.id = p_id
        self.department = ""
        self.renege_time = 0
        self.priority = 0
        self.priority_update = 0
        self.sdec_other_priority = 0.8

class Model:
    def __init__(self, run_number):
        self.env = simpy.Environment()
        self.event_log = []
        self.patient_counter = 0
        self.nelbed = simpy.PriorityResource(
            self.env, capacity=g.number_of_nelbeds)
        self.run_number = run_number

        # Initialise distributions for generators
        self.ed_inter_visit_dist = Exponential(mean = g.ed_inter_visit, random_seed = self.run_number*2)
        self.sdec_inter_visit_dist = Exponential(mean = g.sdec_inter_visit, random_seed = self.run_number*3)
        self.other_inter_visit_dist = Exponential(mean = g.other_inter_visit, random_seed = self.run_number*4)
        self.mean_time_in_bed_dist = Lognormal(g.mean_time_in_bed, g.sd_time_in_bed, random_seed = self.run_number*5)
        self.renege_time = Uniform(0, 9000, random_seed = self.run_number*6)
        self.priority_update = Uniform(0, 9000, random_seed = self.run_number*7)
        self.priority = Uniform(1,2, random_seed = self.run_number*8)
    
    def generator_ed_arrivals(self): #ed patients
        while True:
            self.patient_counter += 1
            p = Patient(self.patient_counter)
            p.department = "ED"
            p.renege_time = self.renege_time.sample()
            p.priority = round(self.priority.sample())
            p.priority_update = self.priority_update.sample()
            self.env.process(self.attend_ed(p))

            sampled_inter = self.ed_inter_visit_dist.sample() # time to next patient arriving
            yield self.env.timeout(sampled_inter)
    
    def generator_sdec_arrivals(self):
        while True:
            self.patient_counter += 1
            p = Patient(self.patient_counter)
            p.department = "SDEC"
            p.priority = 0.8 # set all sdec patients as high priority
            self.env.process(self.attend_sdec(p))

            sampled_inter = self.sdec_inter_visit_dist.sample()
            yield self.env.timeout(sampled_inter)

    def generator_other_arrivals(self):
        while True:
            self.patient_counter += 1
            p = Patient(self.patient_counter)
            p.department = "Other"
            p.priority = 0.8 # set all other patients as high priority
            self.env.process(self.attend_other(p))

            sampled_inter = self.other_inter_visit_dist.sample()
            yield self.env.timeout(sampled_inter)

    def attend_ed(self, patient):
        self.event_log.append(
            {'patient' : patient.id,
             'pathway' : patient.department,
             'event_type' : 'arrival_departure',
             'event' : 'arrival',
             'time' : self.env.now}
        )
        
        self.event_log.append(
            {'patient' : patient.id,
             'pathway' : patient.department,
             'event_type' : 'queue',
             'event' : 'admission_wait_begins',
             'time' : self.env.now}
        )

        with self.nelbed.request(priority=patient.priority) as req:
            # Wait until one of 3 things happens....
            result_of_queue = (yield req | # they get a bed
                               self.env.timeout(patient.renege_time) | # they renege
                               self.env.timeout(patient.priority_update)) # they become higher priority

            # if the result is they get a bed, record the relevant details
            if req in result_of_queue:
                self.event_log.append(
                {'patient' : patient.id,
                'pathway' : patient.department,
                'event_type' : 'resource_use',
                'event' : 'admission_begins',
                'time' : self.env.now,
                }
                )
                
                sampled_bed_time = self.mean_time_in_bed_dist.sample()
                yield self.env.timeout(sampled_bed_time)

                self.event_log.append(
                {'patient' : patient.id,
                'pathway' : patient.department,
                'event_type' : 'resource_use_end',
                'event' : 'admission_complete',
                'time' : self.env.now}
                )

                self.event_log.append(
                {'patient' : patient.id,
                'pathway' : patient.department,
                'event_type' : 'arrival_departure',
                'event' : 'depart',
                'time' : self.env.now}
                )
            
            # If the result of the queue was increase of priority
            elif patient.priority_update < patient.renege_time:
                patient.priority = patient.priority - 2.2 #arbitrary deterioration
                self.event_log.append(
                {'patient' : patient.id,
                'pathway' : patient.department,
                'event_type' : 'other',
                'event' : 'priority_increase',
                'time' : self.env.now,
                }
                )
                # Make another bed request with new priority
                with self.nelbed.request(priority=patient.priority) as req:
                    yield req
                    self.event_log.append(
                    {'patient' : patient.id,
                    'pathway' : patient.department,
                    'event_type' : 'resource_use',
                    'event' : 'admission_begins',
                    'time' : self.env.now,
                    }
                    )
                
                    sampled_bed_time = self.mean_time_in_bed_dist.sample()
                    yield self.env.timeout(sampled_bed_time)

                    self.event_log.append(
                    {'patient' : patient.id,
                    'pathway' : patient.department,
                    'event_type' : 'resource_use_end',
                    'event' : 'admission_complete',
                    'time' : self.env.now}
                    )

                    self.event_log.append(
                    {'patient' : patient.id,
                    'pathway' : patient.department,
                    'event_type' : 'arrival_departure',
                    'event' : 'depart',
                    'time' : self.env.now}
                    )
            
            # If patient reneges
            else:
                self.event_log.append(
                    {'patient' : patient.id,
                    'pathway' : patient.department,
                    'event_type' : 'other',
                    'event' : 'renege',
                    'time' : self.env.now,
                    }
                    )
                
                self.event_log.append(
                    {'patient' : patient.id,
                    'pathway' : patient.department,
                    'event_type' : 'arrival_departure',
                    'event' : 'depart',
                    'time' : self.env.now}
                    )
    
    def attend_sdec(self, patient):
        self.event_log.append(
            {'patient' : patient.id,
             'pathway' : patient.department,
             'event_type' : 'arrival_departure',
             'event' : 'arrival',
             'time' : self.env.now}
        )

        self.event_log.append(
            {'patient' : patient.id,
             'pathway' : patient.department,
             'event_type' : 'queue',
             'event' : 'admission_wait_begins',
             'time' : self.env.now}
        )

        with self.nelbed.request(priority=patient.priority) as req:
            yield req
            self.event_log.append(
                {'patient' : patient.id,
                'pathway' : patient.department,
                'event_type' : 'resource_use',
                'event' : 'admission_begins',
                'time' : self.env.now,
                }
                )
            
            sampled_bed_time = self.mean_time_in_bed_dist.sample()
            yield self.env.timeout(sampled_bed_time)

        self.event_log.append(
        {'patient' : patient.id,
        'pathway' : patient.department,
        'event_type' : 'resource_use_end',
        'event' : 'admission_complete',
        'time' : self.env.now}
        )

        self.event_log.append(
        {'patient' : patient.id,
        'pathway' : patient.department,
        'event_type' : 'arrival_departure',
        'event' : 'depart',
        'time' : self.env.now}
        )

    def attend_other(self, patient):
        self.event_log.append(
            {'patient' : patient.id,
             'pathway' : patient.department,
             'event_type' : 'arrival_departure',
             'event' : 'arrival',
             'time' : self.env.now}
        )

        self.event_log.append(
            {'patient' : patient.id,
             'pathway' : patient.department,
             'event_type' : 'queue',
             'event' : 'admission_wait_begins',
             'time' : self.env.now}
        )

        with self.nelbed.request(priority=patient.sdec_other_priority) as req:
            yield req
            self.event_log.append(
                {'patient' : patient.id,
                'pathway' : patient.department,
                'event_type' : 'resource_use',
                'event' : 'admission_begins',
                'time' : self.env.now,
                }
                )
            
            sampled_bed_time = self.mean_time_in_bed_dist.sample()
            yield self.env.timeout(sampled_bed_time)

        self.event_log.append(
        {'patient' : patient.id,
        'pathway' : patient.department,
        'event_type' : 'resource_use_end',
        'event' : 'admission_complete',
        'time' : self.env.now}
        )

        self.event_log.append(
        {'patient' : patient.id,
        'pathway' : patient.department,
        'event_type' : 'arrival_departure',
        'event' : 'depart',
        'time' : self.env.now}
        )

    def run(self):
        self.env.process(self.generator_ed_arrivals())
        self.env.process(self.generator_sdec_arrivals())
        self.env.process(self.generator_other_arrivals())
        self.env.run(until=(g.sim_duration + g.warm_up_period))
        self.event_log = pd.DataFrame(self.event_log)
        self.event_log["run"] = self.run_number
        return {'event_log':self.event_log}

class Trial:
    def  __init__(self):
        self.all_event_logs = []
        self.patient_df = pd.DataFrame()

    def run_trial(self):
        for run in range(g.number_of_runs):
            my_model = Model(run)
            model_outputs = my_model.run()
            event_log = model_outputs["event_log"]
            
            self.all_event_logs.append(event_log)
        self.all_event_logs = pd.concat(self.all_event_logs)
        self.wrangle_data()
        return self.all_event_logs, self.patient_df
    
    def wrangle_data(self):
        df = self.all_event_logs[["patient", "event", "time", "run", "pathway"]]
        df = df.pivot(index=["patient","run", "pathway"], columns="event", values="time")
        df = (df.reset_index()
                .rename_axis(None,axis=1))
        df["total_los"] = df["depart"] - df["arrival"]
        df["q_time"] = df["admission_begins"] - df["admission_wait_begins"]
        df["treatment_time"] = df["admission_complete"] - df["admission_begins"]
        self.patient_df = df
    

#For testing
my_trial = Trial()
print(f"Running {g.number_of_runs} simulations......")
all_event_logs, ecds =  my_trial.run_trial()
display(my_trial.all_event_logs.head(1000))
display(my_trial.patient_df.tail(1000))