from re import L


# knowledgeList = [1,2,3,4,5,6,1,2,5,4,3,6,2,1,4,2,6,7,8]
# KnowledgeCount = {}
# for i in range(1, 9):
#     KnowledgeCount[i] = knowledgeList.count(i)

# non_knowledgeList = [x[0] for x in KnowledgeCount.items() if x[1] == 0]
# if len(non_knowledgeList):
#     print(True)
# else:
#     print(False)
# print(len(non_knowledgeList))

from datetime import datetime,timedelta
t1 = timedelta(hours=3)
t2 = timedelta(hours=2)

print(min(t1, t2))
