-- Demo logins. Passwords here are hashed by setup.js right after this file runs. Safe to re-run.
insert into users (name, email, phone, role, password_hash) values
  ('Admin',            'admin@finxl.com',      null, 'admin',      'admin123'),
  ('Operations Demo',  'operations@finxl.com', null, 'operations', 'operations123'),
  ('Trainer Demo',     'trainer@finxl.com',   null, 'trainer',    'trainer123'),
  ('Placement Demo',   'placement@finxl.com', null, 'placement',  'placement123'),
  ('Student Demo',     'student@finxl.com',   null, 'student',    'student123')
on conflict (email) do nothing;

insert into students (user_id, college, degree, city, target_roles)
select id, 'Demo College', 'MBA Finance', 'Pune', array['Financial Analyst']
from users where email = 'student@finxl.com'
on conflict (user_id) do nothing;

insert into trainers (user_id, skills, weekly_capacity)
select id, array['Excel', 'Financial Modelling', 'Valuation'], 10
from users where email = 'trainer@finxl.com'
on conflict (user_id) do nothing;

-- Demo students to rank in drives (no password: they cannot log in). Skills/experience live in students.extra.
with demo(name, email, city, roles, skills, years) as (values
  ('Aarav Mehta',  'aarav@demo.finxl.com',  'Mumbai', array['Financial Analyst'],      array['Excel','Financial Modeling','Valuation','FP&A'],  1),
  ('Diya Shah',    'diya@demo.finxl.com',   'Pune',   array['Equity Research Analyst'], array['Excel','Valuation','Equity Research'],            0),
  ('Rohan Iyer',   'rohan@demo.finxl.com',  'Mumbai', array['Business Analyst'],        array['Excel','SQL','Power BI'],                         2),
  ('Sneha Kulkarni','sneha@demo.finxl.com', 'Pune',   array['Financial Analyst'],       array['Excel','Financial Modeling'],                     0)
), u as (
  insert into users (name, email, role)
  select name, email, 'student' from demo on conflict (email) do nothing returning id, email
)
insert into students (user_id, city, target_roles, extra)
select u.id, d.city, d.roles, jsonb_build_object('skills', to_jsonb(d.skills), 'experience_years', d.years)
from u join demo d using (email)
on conflict (user_id) do nothing;
