# Model Progression and Experiment Notes

This document summarizes the progression of reinforcement learning models and key observations during the development of the Zelda RL project. Each model iteration includes changes to reward parameters, environment tweaks, and notable behaviors or issues encountered.

---

## Model Progression

1. **Model 1**
   - Learned to leave the house quickly after episode 22.
   - Congestion at tile change area due to area discovery reward bug.
   - Issue thought to be fixed in Model 1.

2. **Model 2**
   - Introduced negative reward for reaching the same coordinate more than 5 times (penalty increases with frequency).
   - Reached left side of castle grounds; traffic jam due to unmarked area.
   - Data collection error: too many coords recorded as new due to unmarked area.

3. **Model 3**
   - Changed rupee reward from 0.1 to 1.
   - Area discovery reward increased from 5 to 10.
   - Discovered sword, basement rooms, and secret entrance around episode 62.
   - After episode 110, AI avoided castle grounds, focusing on Link's land and new coordinates.
   - First encounters with enemies deterred further exploration into the castle.

4. **Model 4**
   - Death penalty decreased from -1 to -0.2.
   - Area discovery reward increased to 20.
   - Explore locations reward made delta-based.
   - Added reward for enemies killed (5).

5. **Model 5**
   - Same as Model 4, but FPS set back to 60 (from 1).
   - Model 4 had a bug in env 4, episode 32.

6. **Model 5.01**
   - Another training session of Model 5.
   - Reached inside the castle, but exploration not worthwhile due to guards.

7. **Model 6**
   - Proper death count implementation.
   - Reward weights:
     - reward_scale=1.0
     - explore_weight=0.1
     - area_discovery_weight=50.0
     - rupee_weight=1.0
     - health_weight=1.0
     - sword_weight=75.0
     - enemies_killed_weight=7.5
     - small_key_weight=15.0

8. **Model 6.01-6.02**
   - Reached entrance but prioritized unexplored left side inside castle walls.
   - Increased step size, lowered episode count, lowered update frequency, increased env to 12.

9. **Model 7**
   - Update frequency may have caused stagnation.

10. **Model 8**
    - Added reward tracking and graphs.
    - Realized delta of a delta was being used as reward.
    - Removed linear scaling of revisit penalty.
    - Weights:
      - explore_weight=0.1
      - revisit_weight=-0.01

11. **Model 9**
    - Same issue as Model 8 with stagnation, more frequent due to lower revisit reward.

12. **Model 10**
    - Switched to SubprocVecEnv for multiprocessing.
    - Still investigating stagnation.
    - Movements toward corners of Link's land and guards.

13. **Model 11**
    - Increased revisit penalty to -0.2.
    - Stagnation occurs later; movements to bottom and top right corners.

14. **Model 12**
    - Removed revisit reward; did not solve stagnation.

15. **Model 13/13.01**
    - Stronger explore reward; stagnation persists.
      - explore_weight=1.0
      - revisit_weight=0.0

16. **Model 14**
    - Larger batch size (512); no effect.

17. **Model 15**
    - Update frequency set to 4096 steps, ent_coef to 0.05.

18. **Model 16**
    - Update frequency 4096 steps, ent_coef 0.2.
    - ent_coef negatively correlated with stagnation frequency.

19. **Model 17**
    - Update frequency 2048 steps, ent_coef 0.2.
      - explore_weight=2.0
      - revisit_weight=-0.1

20. **Model 18**
    - Delta of a delta for all rewards.

21. **Model 19**
    - Delta of a delta for all rewards, linear scaling of revisit penalty.
      - explore_weight=0.1
      - revisit_weight=-0.1

22. **Model 20**
    - Delta of a delta for all rewards, ent_coef 0.01, num_env 8 (replica of Model 6).
    - Makes it inside the castle, but after 12M timesteps, prefers Link's land for more reward.

23. **Model 21**
    - Stuck at bridge; revisit penalty -0.01.

24. **Model 22**
    - Delta of delta for explore only.
      - explore_weight=0.1
      - revisit_weight=-0.1

25. **Model 23**
    - Same args as 17, removes linear scaling of revisit penalty, all delta of delta.
      - explore_weight=2.0
      - revisit_weight=-0.1
      - area_discovery_weight=200.0
      - rupee_weight=1.0
      - health_weight=1.0
      - sword_weight=75.0
      - enemies_killed_weight=20.0
      - small_key_weight=15.0

26. **Model 24**
    - Only 10% of explore and revisit rewards; stagnation worse.
      - explore_weight=0.2
      - revisit_weight=-0.01

27. **Model 25**
    - Test reward scale's influence on stagnation; worse results.
      - reward_scale=10.0
      - explore_weight=0.2
      - revisit_weight=-0.01
      - area_discovery_weight=200.0
      - rupee_weight=1.0
      - health_weight=1.0
      - sword_weight=150.0
      - enemies_killed_weight=50.0
      - small_key_weight=15.0

28. **Model 26**
    - New reward values, 5000 step intervals.
      - reward_scale=1.0
      - explore_weight=2.0
      - revisit_weight=-0.05
      - area_discovery_weight=10.0
      - rupee_weight=0.5
      - health_weight=0.5
      - sword_weight=10.0
      - enemies_killed_weight=2.0
      - small_key_weight=5.0

29. **Model 27**
    - Same as 26, but 10,000 step intervals.

30. **Model 28**
    - Same as 23, but 10,000 step intervals.

31. **Model 29**
    - Same as 23, but 20,000 step intervals.

32. **Model 30**
    - Same as 26, but 20,000 step intervals.

---

## Ongoing Issue: Agent Stagnation and Exploration Collapse

Across several models, a recurring issue has emerged: after an initial phase of exploration and learning, the agent suddenly gets stuck inside Link's house, only moving to a few new tiles. In earlier episodes, the agent would go outside and discover many more tiles, but this behavior collapses as training progresses.

To address this, I have tested different variables and reward configurations:
- **Model 10:** Base model.
- **Model 11:** Increased revisit penalty (revisit_weight = -0.2), which delayed but did not prevent stagnation. The agent's movement shifted to the bottom and top right corners of Link's land.
- **Model 12:** Removed revisit reward entirely, but the issue persisted.
- **Model 13/13.01:** Increased explore reward (explore_weight = 1.0, revisit_weight = 0.0), but stagnation remained unsolved.
- **Model 14:** Increased batch size to 512, with no effect on the issue.

Despite these changes, all models eventually exhibit a similar pattern: initial exploration followed by getting stuck in a small area. I suspect this may be due to **catastrophic forgetting**, where the agent forgets previously learned behaviors as it continues to train.

If you have experience with reinforcement learning and have encountered or solved similar issues, your insights would be greatly appreciated! Please reach out or contribute suggestions to help address this challenge.

You can view this pattern visually in the reward progress graphs located at `ZeldaALTTP/visualization/statistics/Model Graphs`. These graphs illustrate how the agent's reward changes over time and make the stagnation issue clear.

These notes reflect ongoing experimentation and tuning. Stagnation, reward shaping, and exploration remain key challenges. If you have insights or suggestions, please reach out or contribute! 