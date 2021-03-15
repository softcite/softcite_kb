import re 
import sys

from software_kb.arango_common import aggregate_no_merge, aggregate_with_merge

entity1 = {}

entity2 = {}

print("entity1:", entity1)
print("entity2:", entity2)
result = aggregate_no_merge(entity1, entity2)
print("aggregate_no_merge:", result)

result = aggregate_with_merge(entity1, entity2)
print("aggregate_nwith_merge:", result)
