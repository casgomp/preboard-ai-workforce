-- Fictional hackathon demo data. Dates stay current relative to execution day.
INSERT OVERWRITE employees VALUES
('E001','Anna Müller','Software Engineer','Digital Engineering','Wolfsburg','Sarah Weber',date_add(current_date(),5),'anna.mueller@example.demo'),
('E002','David Klein','Product Manager','Product Strategy','Berlin','Nina Hoffmann',date_add(current_date(),3),'david.klein@example.demo'),
('E003','Maria Rossi','Data Engineer','Data Platforms','Munich','Jonas Bauer',date_add(current_date(),8),'maria.rossi@example.demo'),
('E004','Lukas Schmidt','UX Designer','Design','Wolfsburg','Lea König',date_add(current_date(),1),'lukas.schmidt@example.demo'),
('E005','Sofia Garcia','Data Analyst','Business Intelligence','Berlin','David Neumann',date_add(current_date(),12),'sofia.garcia@example.demo');

INSERT OVERWRITE day_one_requirements VALUES
('R01','contract_status','Contract','HR',5,true),('R02','payroll_status','Payroll','HR',2,false),
('R03','employee_account','Employee account','IT',8,true),('R04','laptop_status','Laptop','IT',20,true),
('R05','software_access','Software permissions','IT',4,true),('R06','badge_status','Building badge','FACILITIES',4,true),
('R07','manager_assigned','Manager assignment','HR',2,true),('R08','welcome_meeting','Welcome meeting','MANAGER',2,true),
('R09','day_one_agenda','Day-one agenda','MANAGER',3,true),('R10','orientation_status','Orientation','ONBOARDING',2,false),
('R11','parking_status','Parking','FACILITIES',5,false);

INSERT OVERWRITE day_one_facts
SELECT concat(e.employee_id,'-',r.requirement_id), e.employee_id, r.fact_key,
  CASE WHEN e.employee_id='E002' AND r.fact_key='badge_status' THEN 'DELAYED'
       WHEN e.employee_id IN ('E001','E003','E005') AND r.fact_key='parking_status' THEN 'IN_PROGRESS'
       WHEN e.employee_id IN ('E003','E005') AND r.fact_key='orientation_status' THEN 'IN_PROGRESS'
       ELSE 'READY' END,
  r.category,
  CASE r.category WHEN 'HR' THEN 'HR Core' WHEN 'IT' THEN 'IT Asset Management' WHEN 'FACILITIES' THEN 'Facilities Access' WHEN 'MANAGER' THEN 'Manager Workspace' ELSE 'Learning Platform' END,
  CASE r.category WHEN 'HR' THEN 'People Operations' WHEN 'IT' THEN 'Workplace IT' WHEN 'FACILITIES' THEN 'Facilities' WHEN 'MANAGER' THEN 'Hiring Manager' ELSE 'People Development' END,
  current_timestamp(),
  CASE WHEN r.fact_key IN ('contract_status','payroll_status') THEN 'INTERNAL' ELSE 'CANDIDATE_SAFE' END,
  'SYSTEM_REPORTED', null, null, r.requirement_name
FROM employees e CROSS JOIN day_one_requirements r;

INSERT OVERWRITE company_knowledge VALUES
('K01','Wolfsburg arrival','arrival','Wolfsburg','Fictional demo: arrive at the North Lobby at 08:45 with photo ID.'),
('K02','Dress guidance','dress',null,'Fictional demo: smart casual is a comfortable choice.'),
('K03','Orientation','orientation',null,'Fictional demo: orientation covers company basics, safety and support contacts.');

INSERT OVERWRITE department_contacts VALUES
('Workplace IT','Michael Braun','workplace-it@dayone.demo',array('account','device','laptop','software')),
('Facilities','Laura Stein','facilities@dayone.demo',array('badge','building','office','parking')),
('People Operations','Julia Hartmann','people-operations@dayone.demo',array('contract','payroll','policy','tax')),
('Learning & Onboarding','Felix Weber','onboarding@dayone.demo',array('orientation','training'));
