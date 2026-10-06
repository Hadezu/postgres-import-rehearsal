-- All fixture people and businesses are synthetic. No upstream personal data.
INSERT INTO employee(employee_id,first_name,last_name) VALUES(1,'Demo','Operator');
INSERT INTO customer(customer_id,first_name,last_name,email,company,country,support_rep_id,address)
VALUES (1,'Ada','Sample','ada@example.invalid','Old Demo','Poland',1,'Synthetic address 1'),
       (2,'Noah','Example','noah@example.invalid','Studio Demo','Poland',1,NULL);
INSERT INTO invoice(invoice_id,customer_id,invoice_date,total,billing_country)
VALUES(1,1,'2026-10-01',120.50,'Poland');
