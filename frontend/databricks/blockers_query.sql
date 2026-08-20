-- Starting within 7 days with delayed critical facts.
SELECT e.employee_id, e.name, e.start_date, f.fact_key, f.fact_value, f.owner_team, f.source_system
FROM employees e
JOIN day_one_facts f USING (employee_id)
JOIN day_one_requirements r USING (fact_key)
WHERE e.start_date <= date_add(current_date(), 7)
  AND r.critical_for_day_one = true
  AND f.fact_value IN ('DELAYED','BLOCKED','MISSING')
QUALIFY row_number() OVER (PARTITION BY e.employee_id, f.fact_key ORDER BY f.last_updated DESC) = 1;

-- Unresolved Day One blockers.
SELECT e.name, e.start_date, f.fact_key, f.fact_value, f.owner_team,
  datediff(e.start_date, current_date()) AS days_remaining
FROM employees e JOIN day_one_facts f USING (employee_id)
WHERE f.fact_value IN ('BLOCKED','MISSING')
ORDER BY days_remaining;
