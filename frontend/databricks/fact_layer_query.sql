-- Trusted current state: source, owner, value, freshness, visibility and prior state.
SELECT
  e.employee_id, e.name, e.role, e.location, e.start_date,
  f.fact_key, f.candidate_safe_label, f.fact_value, f.previous_value,
  f.category, f.source_system, f.owner_team, f.last_updated,
  f.visibility, f.verification_status
FROM employees e
JOIN day_one_facts f USING (employee_id)
QUALIFY row_number() OVER (PARTITION BY e.employee_id, f.fact_key ORDER BY f.last_updated DESC) = 1;

-- Employees starting in the next 14 days.
SELECT employee_id, name, role, location, start_date
FROM employees
WHERE start_date BETWEEN current_date() AND date_add(current_date(), 14)
ORDER BY start_date;

-- Latest fact changes.
SELECT employee_id, fact_key, previous_value, new_value, source_system, event_timestamp
FROM fact_events
ORDER BY event_timestamp DESC
LIMIT 100;

-- Preparation facts grouped by accountable team.
SELECT owner_team, fact_value, count(*) AS fact_count
FROM day_one_facts
GROUP BY owner_team, fact_value
ORDER BY owner_team, fact_value;
