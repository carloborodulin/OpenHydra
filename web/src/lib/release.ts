import { createContext, useContext } from "react";
import type { Snapshot } from "./api";

/** The data release on screen, for exports and captions (App provides it). */
export const ReleaseContext = createContext<Snapshot | null>(null);
export const useRelease = () => useContext(ReleaseContext);
