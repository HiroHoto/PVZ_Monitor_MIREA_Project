# Event Storming Model for PVZ Monitoring System

[User] -> (Login) -> [User Authenticated]

[Operator] -> (Register Operation) -> [Operation Data Received]
[Operation Data Received] -> (Validate Operation) -> [Operation Validated]
[Operation Data Received] -> (Validate Operation) -> [Validation Failed]

[Validation Failed] -> (Log Error) -> [Error Logged]

[Operation Validated] -> (Save Operation) -> [Operation Recorded]
[Operation Recorded] -> (Check Capacity) -> [Load Calculated]

[Load Calculated] -> (Compare with Capacity) -> [Overload Detected]
[Load Calculated] -> (Compare with Capacity) -> [Normal Load Confirmed]

[Supervisor/Analyst] -> (Request Report) -> [Report Generated]
[Supervisor/Analyst] -> (Export CSV) -> [CSV File Ready]
