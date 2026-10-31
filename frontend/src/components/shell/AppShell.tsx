import type { PropsWithChildren } from "react";

import lockup from "../../assets/statx-lockup.png";
import { LocalRuntimeStatus } from "./LocalRuntimeStatus";
import { SidebarNavigation } from "./SidebarNavigation";
import { TopRuntimeBar } from "./TopRuntimeBar";

export type ShellLayout = "desktop" | "tablet-landscape" | "tablet-portrait";

export function AppShell({ children, layout = "desktop" }: PropsWithChildren<{ layout?: ShellLayout }>) {
  return (
    <div className={`app-shell layout-${layout}`}>
      <aside className="sidebar">
        <img className="brand-lockup" src={lockup} alt="Stat X — Football Data Lab" />
        <SidebarNavigation />
        <div className="sidebar-runtime"><LocalRuntimeStatus /></div>
      </aside>
      <div className="app-column">
        <TopRuntimeBar />
        <main className="workspace" id="main-content">{children}</main>
      </div>
    </div>
  );
}
