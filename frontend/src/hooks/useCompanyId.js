import { useParams } from "react-router-dom";

export default function useCompanyId() {
  const { companyId } = useParams();
  return [companyId || "", () => {}];
}
