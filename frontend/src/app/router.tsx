import { createBrowserRouter } from "react-router-dom";

import { SessionGate } from "../features/auth/SessionGate";

export const router = createBrowserRouter([{ path: "*", element: <SessionGate /> }]);
