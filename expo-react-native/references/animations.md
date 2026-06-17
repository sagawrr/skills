# Animations — Reanimated 4 + New Architecture

> Verified against: software-mansion-labs/skills animations SKILL.md, Reanimated 4 docs

## Critical: Breaking Changes from Reanimated 3

| Reanimated 3 | Reanimated 4 |
|---|---|
| `runOnJS(fn)(args)` | `scheduleOnRN(fn, ...args)` from `react-native-worklets` |
| Manual babel plugin | Auto-configured via New Architecture |
| JS-thread layout animations | Native-thread layout animations (smoother) |

`runOnJS` does not exist in Reanimated 4. Every occurrence is a crash. Replace all of them.

```tsx
import { scheduleOnRN } from 'react-native-worklets';

// ❌ Reanimated 3 — crashes in Reanimated 4
useAnimatedScrollHandler({
  onScroll: (e) => { runOnJS(setHeader)(e.contentOffset.y > 100); },
});

// ✅ Reanimated 4
useAnimatedScrollHandler({
  onScroll: (e) => {
    scrollY.value = e.contentOffset.y;
    if (e.contentOffset.y > 100) scheduleOnRN(setHeader, true);
  },
});
```

---

## Choosing the Right Animation Approach

| Scenario | Use |
|---|---|
| Simple show/hide, color change, move | CSS transitions (Reanimated 4) |
| Gesture-driven animation | `useSharedValue` + `useAnimatedStyle` |
| Scroll-driven animation | `useAnimatedScrollHandler` + `useSharedValue` |
| Enter/exit screen transitions | Layout animations |
| Shared element transition | `sharedTransitionTag` |
| Canvas / particle / shader | React Native Skia / react-native-wgpu |

---

## CSS Transitions (Reanimated 4 — New Architecture only)

```tsx
import Animated from 'react-native-reanimated';

// Simple opacity toggle — no useSharedValue needed
<Animated.View
  style={{
    transition: { opacity: { duration: 300, easing: 'ease-out' } },
    opacity: isVisible ? 1 : 0,
  }}
/>

// Multiple properties
<Animated.View
  style={{
    transition: {
      transform: { duration: 200 },
      opacity: { duration: 150 },
    },
    transform: [{ scale: pressed ? 0.95 : 1 }],
    opacity: disabled ? 0.4 : 1,
  }}
/>
```

---

## Shared Value Animations

```tsx
import { useSharedValue, useAnimatedStyle, withSpring, withTiming, useDerivedValue } from 'react-native-reanimated';

const offset = useSharedValue(0);

// ✅ Only animate GPU-composited properties
const style = useAnimatedStyle(() => ({
  transform: [
    { translateX: withSpring(offset.value) },
    { scale: withTiming(scale.value, { duration: 200 }) },
  ],
  opacity: withTiming(visible.value ? 1 : 0),
}));

// ❌ Never animate layout properties — triggers layout on every frame
// width, height, top, left, margin, padding, borderWidth
```

### `useDerivedValue` — derive animated values without reactions

```tsx
// ✅ efficient — no observer pattern overhead
const headerOpacity = useDerivedValue(() =>
  interpolate(scrollY.value, [0, 100], [0, 1], Extrapolation.CLAMP)
);

// useAnimatedReaction is for side effects only (rare)
// useDerivedValue is for derived animated values (most cases)
```

---

## Scroll-Driven Animations

```tsx
const scrollY = useSharedValue(0);

const scrollHandler = useAnimatedScrollHandler({
  onScroll: (e) => {
    scrollY.value = e.contentOffset.y;
  },
  onBeginDrag: () => {
    // worklet context — use scheduleOnRN for JS calls
  },
});

// Connect to Animated.ScrollView (not plain ScrollView)
<Animated.ScrollView onScroll={scrollHandler} scrollEventThrottle={16}>
```

---

## Gesture Handler v2/v3

```tsx
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

// Tap with animated press state — prefer over Pressable for animated UIs
const tap = Gesture.Tap()
  .onBegin(() => { scale.value = withSpring(0.95); })
  .onFinalize(() => { scale.value = withSpring(1); });

// Pan gesture
const pan = Gesture.Pan()
  .onUpdate(e => { x.value = e.translationX; })
  .onEnd(() => { x.value = withSpring(0); });

// Compose gestures
const composed = Gesture.Simultaneous(tap, pan);

<GestureDetector gesture={composed}>
  <Animated.View style={animatedStyle} />
</GestureDetector>
```

---

## Layout Animations (Enter/Exit)

```tsx
import { FadeIn, FadeOut, SlideInRight, LinearTransition } from 'react-native-reanimated';

// Enter/exit animations
<Animated.View entering={FadeIn.duration(200)} exiting={FadeOut.duration(150)}>

// List item reorder animation — attach to the list item
<Animated.View layout={LinearTransition}>

// Shared element transition
<Animated.Image sharedTransitionTag={`image-${item.id}`} source={{ uri: item.imageUri }} />
// In destination screen:
<Animated.Image sharedTransitionTag={`image-${item.id}`} source={{ uri: item.imageUri }} />
```

---

## 120fps Setup

```tsx
// app.json — enable high frame rate rendering
{
  "expo": {
    "plugins": [
      ["react-native-reanimated", { "framerate": 120 }]
    ]
  }
}
```

Only effective on ProMotion displays (iPhone 13 Pro+, iPad Pro). Verify with `useFrameCallback` timing.

---

## Performance Rules

- Animated style objects must be created with `useAnimatedStyle` — plain JS objects re-render on every frame
- Shared values live on the UI thread — never read `.value` in `useAnimatedStyle` outside the worklet (it's synchronous on UI thread)
- Use `cancelAnimation(sharedValue)` before starting a new animation on the same value to prevent fighting animations
- `useFrameCallback` for per-frame logic — not `setInterval`
- Worklet closures capture values by reference — large objects in closures waste UI thread memory; capture only primitives

---

## Accessibility

```tsx
import { useReducedMotion, ReducedMotionConfig } from 'react-native-reanimated';

// Per-component
function AnimatedCard() {
  const reduceMotion = useReducedMotion();
  const entering = reduceMotion ? undefined : FadeIn;
  return <Animated.View entering={entering}>{children}</Animated.View>;
}

// Global — wrap app root
<ReducedMotionConfig mode="always"> // or "system"
  <App />
</ReducedMotionConfig>
```
