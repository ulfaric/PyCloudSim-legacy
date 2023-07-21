The class "vCPU" is an implementation derived from the "PhysicalComponent" class. A "vCPU" object consists of multiple "vCPUCore" instances and a cache that serves as a pool for storing "vProcess" objects. Whenever a new "vProcess" is added to the cache or a "vProcess" is terminated, the "vCPU" class handles the assignment of "vProcess" objects to its corresponding "vCPUCore" based on several factors. These factors include the priority of the "vProcess," the available computational power of each "vCPUCore," and the allowed CPU time of the associated "vContainer." Notably, a single "vProcess" can be assigned to multiple "vCPUCore" instances, allowing for simulated parallel execution. The scheduling of "vProcess" is implemented as an event with only one scheduling event being active for each "vCPU" at any given time.

:::PyCloudSim.entity.v_cpu.vCPU