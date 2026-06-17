# Animations — Reanimated 4

> Verified: software-mansion-labs/skills animations SKILL.md

## Breaking Change: `runOnJS` → `scheduleOnRN`

`runOnJS` does not exist in Reanimated 4. Every call is a crash. Replace all occurrences.

```tsx
import { scheduleOnRN } from 'react-native-worklets';

// ❌ Reanimated 3 pattern — crashes
onScroll: (e) => { runOnJS(setHeader)(e.contentOffset.y > 100); }

// ✅ Reanimated 4
onScroll: (e) => {
  scrollY.value = e.contentOffset.y;
  if (e.contentOffset.y > 100) scheduleOnRN(setHeader, true);
}
```

---

## Choosing the Right Approach

| Scenario | Use |
|---|---|
| Simple show/hide, color, position change | CSS transitions (New Architecture only) |
| Gesture-driven | `useSharedValue` + `useAnimatedStyle` |
| Scroll-driven | `useAnimatedScrollHandler` + `useSharedValue` |
| Enter/exit screen | Layout animations |
| Shared element | `sharedTransitionTag` |
| Canvas / particle / shader | React Native Skia / react-native-wgpu |

---

## CSS Transitions (Reanimated 4, New Architecture only)

```tsx
// No useSharedValue needed for simple transitions
<Animated.View
  style={{
    transition: {
      opacity: { duration: 300, easing: 'ease-out' },
      transform: { duration: 200 },
    },
    opacity: isVisible ? 1 : 0,
    transform: [{ scale: pressed ? 0.95 : 1 }],
  }}
/>
```

---

## Shared Value Animations

Only animate GPU-composited properties — `transform` and `opacity`. Animating `width`, `height`, `top`, `left`, `margin`, `padding` triggers native layout recalculation every frame.

```tsx
const style = useAnimatedStyle(() => ({
  transform: [{ translateX: withSpring(offset.value) }],
  opacity: withTiming(visible.value ? 1 : 0),
}));
```

### `useDerivedValue` over `useAnimatedReaction`

`useDerivedValue` = derived animated value (most cases). `useAnimatedReaction` = side effects only (rare).

```tsx
// ✅ derive with zero observer overhead
const headerOpacity = useDerivedValue(() =>
  interpolate(scrollY.value, [0, 100], [0, 1], Extrapolation.CLAMP)
);
```

---

## Scroll-Driven Animations

```tsx
const scrollY = useSharedValue(0);

const scrollHandler = useAnimatedScrollHandler({
  onScroll: (e) => { scrollY.value = e.contentOffset.y; },
});

// Animated.ScrollView required — not plain ScrollView
<Animated.ScrollView onScroll={scrollHandler} scrollEventThrottle={16}>
```

---

## Gesture Handler

```tsx
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

const tap = Gesture.Tap()
  .onBegin(() => { scale.value = withSpring(0.95); })
  .onFinalize(() => { scale.value = withSpring(1); });

const pan = Gesture.Pan()
  .onUpdate(e => { x.value = e.translationX; })
  .onEnd(() => { x.value = withSpring(0); });

// Compose gestures
const combined = Gesture.Simultaneous(tap, pan);
<GestureDetector gesture={combined}><Animated.View style={style} /></GestureDetector>
```

---

## Layout Animations

```tsx
import { FadeIn, FadeOut, LinearTransition } from 'react-native-reanimated';

<Animated.View entering={FadeIn.duration(200)} exiting={FadeOut.duration(150)}>

// List item reorder
<Animated.View layout={LinearTransition}>

// Shared element — tag must match in both screens
<Animated.Image sharedTransitionTag={`photo-${item.id}`} source={{ uri: item.imageUri }} />
```

---

## 120fps

```json
// app.json
{ "expo": { "plugins": [["react-native-reanimated", { "framerate": 120 }]] } }
```

Only effective on ProMotion displays (iPhone 13 Pro+, iPad Pro).

---

## Performance & Safety Rules

- `cancelAnimation(sv)` before starting a new animation on the same shared value — prevents fighting animations
- Use `useFrameCallback` for per-frame logic, not `setInterval`
- Worklet closures: capture only primitive values — large object captures waste UI thread memory
- `Animated.ScrollView`, not `ScrollView`, when attaching `useAnimatedScrollHandler`

---

## Accessibility

```tsx
import { useReducedMotion, ReducedMotionConfig } from 'react-native-reanimated';

// Per-component
const reduceMotion = useReducedMotion();
<Animated.View entering={reduceMotion ? undefined : FadeIn}>

// Global — wrap app root
<ReducedMotionConfig mode="system"><App /></ReducedMotionConfig>
```
