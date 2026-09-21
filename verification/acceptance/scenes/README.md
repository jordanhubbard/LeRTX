# Independent scene fixtures

These verifier-owned inputs are not generated tests or application source.
They must be used against the admitted application, not substituted for it.

`centimeters-y-up.usda` has centimeter units and a Y-up floor whose top is Y=0.
The ball's local position is `(0, 40, 0)` beneath a parent translated
`(-20, 0, 10)` and scaled by two. Its initial world position is
`(-20, 80, 10)` centimeters, and its world radius is ten centimeters.
Native acceptance must observe the ball fall toward a resting world Y of about
ten centimeters, retain correct visible scale, and preserve authored transforms
on save while simulation poses remain transient. Inspector editing, pause with
camera movement, reset and save/reopen must act on this scene, not an application
replacement fixture. Missing render products/cameras are supplied in the app's
runtime/session layer without modifying the input file merely by opening it.

`unsupported-collider.usda` contains a static triangle-mesh collider. For the
current supported primitive-only Newton import contract, the application must
identify `/World/UnsupportedCollider`, keep visual inspection available, and
disable scene simulation. Silently ignoring the collider is a failed test.

Parsing and coordinate inspection alone verify fixture integrity, not any of
the application behaviors above. Actual frame, pose, control and persistence
observations remain required on both GPU platforms.
