# Module 3: Database Queries Assignment 

## Name

**Rachael Mends**  
**JHED ID:** rmends1

## Module Info

**Module:** Module 3  
**Assignment:** Database Queries Assignment   
**Due Date:** September 20, 2026

## Project Overview

This assignment will introduce you to querying relational databases using SQL and interacting with those databases using an Object-Relational Mapper (ORM)

## SQL vs. SQLAlchemy Comparison

For this comparison, I used Question 11: **What is the average GPA of accepted Princeton University applicants for Fall 2026 who reported a GPA?**

Both approaches produced an average GPA of **3.87**.

### Raw SQL

```sql
SELECT AVG(gpa)
FROM applicants
WHERE LOWER(TRIM(term)) = 'fall 2026'
  AND LOWER(program) LIKE '%princeton%'
  AND LOWER(TRIM(status)) LIKE 'accept%'
  AND gpa IS NOT NULL;
```

### SQLAlchemy

```python
q11_statement = (
    select(func.avg(Applicant.gpa))
    .where(
        and_(
            func.lower(func.trim(Applicant.term)) == "fall 2026",
            func.lower(Applicant.program).like("%princeton%"),
            func.lower(func.trim(Applicant.status)).like("accept%"),
            Applicant.gpa.is_not(None),
        )
    )
)

q11 = session.scalar(q11_statement)
```

### Comparison

Both the raw SQL and SQLAlchemy queries perform the same filtering and aggregation and produce the same average GPA of 3.87, but they express the database operation differently. Raw SQL is more concise and provides direct visibility into the query being executed, which can make straightforward database operations easier to read and debug and gives the programmer precise control over the resulting SQL. SQLAlchemy provides greater abstraction by representing the database through Python classes and attributes, such as `Applicant.gpa`, `Applicant.term`, and `Applicant.status`, rather than requiring the application to work directly with table and column syntax. This abstraction can improve maintainability and portability in larger Python applications because database operations can be constructed and reused using the same Python-based interface as the rest of the application. Therefore, raw SQL offers advantages in conciseness, transparency, and direct control, while SQLAlchemy offers advantages in abstraction, application integration, and maintainability.
