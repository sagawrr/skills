# Animations — Reanimated 4

> Reanimated 4 is stable and requires New Architecture. `scheduleOnRN` is the modern form of `runOnJS` (both work; `scheduleOnRN` is preferred for new code).

---

## Choosing the Right Approach

| Scenario | Use |
|---|---|
| Simple show/hide, color, position | CSS transitions (New Arch only) |
| Gesture-driven | `useSharedValue` + `useAnimatedStyle` |
| Scroll-driven | `useAnimatedScrollHandler` + `useSharedValue` |
| Enter/exit screen | Layout animations |
| Shared element | `sharedTransitionTag` |
| Canvas / shader | React Native Skia / react-native-wgpu |

---

## CSS Transitions (Reanimated 4, New Architecture only)

No `useSharedValue` needed for simple state-driven transitions. Uses flat CSS-style props on the style object:

```tsx
// Single property — scalar values
<Animated.View style={{ transitionProperty: 'opacity', transitionDuration: '300ms', opacity: isVisible ? 1 : 0 }} />

// Multiple properties — arrays (comma-separated strings are wrong)
<Animated.View
  style={{
    transitionProperty: ['opacity', 'transform'],
    transitionDuration: ['300ms', '200ms'],
    transitionTimingFunction: ['ease-out', 'ease-in'],
    opacity: isVisible ? 1 : 0,
    transform: [{ scale: pressed ? 0.95 : 1 }],
  }}
/>
```

---

## Shared Value Animations

Animate **only** `transform` and `opacity` for maximum compatibility. In RN 0.85+ (New Architecture, Shared Animation Backend), `width`, `height`, `top`, `left`, `margin`, and `padding` can also animate with the native driver — but `transform` + `opacity` remain safest for pre-0.85 support.

```tsx
const style = useAnimatedStyle(() => ({
  transform: [{ translateX: withSpring(x.value) }],
  opacity: withTiming(visible.value ? 1 : 0),
}));
```

### `useDerivedValue` — derived animated values

`useDerivedValue` = derive an animated value (zero observer overhead). `useAnimatedReaction` = side effects only (rare).

```tsx
const headerOpacity = useDerivedValue(() =>
  interpolate(scrollY.value, [0, 100], [0, 1], Extrapolation.CLAMP)
);
```

---

## Calling JS from a Worklet

`scheduleOnRN` is the Reanimated 4.1+ preferred API. `runOnJS` still works for compatibility.

```tsx
import { scheduleOnRN } from 'react-native-worklets';

const handler = useAnimatedScrollHandler({
  onScroll: (e) => {
    scrollY.value = e.contentOffset.y;
    // preferred: scheduleOnRN
    // scheduleOnRN(fn, ...args) — single call, unlike runOnJS(fn)(args) double-invocation
    if (e.contentOffset.y > 100) scheduleOnRN(onHeaderVisible);
    // still valid (deprecated): runOnJS(onHeaderVisible)()
  },
});
```

---

## Scroll-Driven Animations

```tsx
const scrollY = useSharedValue(0);
const handler = useAnimatedScrollHandler(e => { scrollY.value = e.contentOffset.y; });

// Must be Animated.ScrollView — not plain ScrollView
<Animated.ScrollView onScroll={handler} scrollEventThrottle={16}>
```

---

## Gesture Handler

```tsx
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

const tap = Gesture.Tap()
  .onBegin(() => { scale.value = withSpring(0.95); })
  .onFinalize(() => { scale.value = withSpring(1); });

// Compose — e.g., simultaneous tap + pan
const combined = Gesture.Simultaneous(tap, pan);
<GestureDetector gesture={combined}><Animated.View style={style} /></GestureDetector>
```

---

## Layout Animations

```tsx
import { FadeIn, FadeOut, LinearTransition } from 'react-native-reanimated';

// Enter/exit
<Animated.View entering={FadeIn.duration(200)} exiting={FadeOut.duration(150)}>

// List reorder
<Animated.View layout={LinearTransition}>

// Shared element — tag must match in source and destination screens
<Animated.Image sharedTransitionTag={`photo-${item.id}`} source={{ uri }} />
```

---

## Performance Rules

- `cancelAnimation(sv)` before starting a new animation on the same shared value
- Worklet closures: capture only primitive values, not object references
- `useFrameCallback` for per-frame logic — not `setInterval`
- 120fps: set `CADisableMinimumFrameDurationOnPhone` to `true` in `Info.plist` (ProMotion devices only — iPhone 13 Pro+, iPad Pro)

---

## Accessibility

```tsx
import { useReducedMotion, ReducedMotionConfig } from 'react-native-reanimated';

const reduceMotion = useReducedMotion();
<Animated.View entering={reduceMotion ? undefined : FadeIn}>

// Global default — wrap app root
<ReducedMotionConfig mode="system"><App /></ReducedMotionConfig>
```
