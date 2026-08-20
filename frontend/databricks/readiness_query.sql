-- Readiness inputs and deterministic weighted contribution.
WITH current_facts AS (
  SELECT * FROM day_one_facts
  QUALIFY row_number() OVER (PARTITION BY employee_id, fact_key ORDER BY last_updated DESC) = 1
), contributions AS (
  SELECT e.employee_id, e.name, e.start_date, r.requirement_name, r.weight, r.critical_for_day_one,
    f.fact_value, f.source_system, f.last_updated,
    r.weight * CASE f.fact_value
      WHEN 'READY' THEN 1.0 WHEN 'TEMPORARY_SOLUTION' THEN 0.9
      WHEN 'IN_PROGRESS' THEN 0.5 WHEN 'DELAYED' THEN 0.2 ELSE 0.0 END AS earned
  FROM employees e CROSS JOIN day_one_requirements r
  LEFT JOIN current_facts f ON f.employee_id=e.employee_id AND f.fact_key=r.fact_key
)
SELECT employee_id, name, start_date,
  round(100 * sum(earned) / sum(weight)) AS readiness_score,
  collect_list(named_struct('requirement',requirement_name,'status',fact_value,'earned',earned,'possible',weight,'source',source_system)) AS explanation
FROM contributions
GROUP BY employee_id, name, start_date
ORDER BY readiness_score, start_date;
