import { useCallback, useState } from "react";

// There's no promoter-auth / company-picker module yet (not in scope until a
// later phase), but every Step 5 endpoint is keyed off company_id. This hook
// just persists whatever company_id the tester enters so it survives reloads
// across the Intake and Upload flows. Swap this out once real auth lands.
const STORAGE_KEY = "sherpa.companyId";

export default function useCompanyId() {
  const [companyId, setCompanyIdState] = useState(
    () => window.localStorage.getItem(STORAGE_KEY) || ""
  );

  const setCompanyId = useCallback((id) => {
    setCompanyIdState(id);
    if (id) {
      window.localStorage.setItem(STORAGE_KEY, id);
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  return [companyId, setCompanyId];
}
