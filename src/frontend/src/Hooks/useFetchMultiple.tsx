import { useState, useEffect } from "react";
import { handleResponse, fetchTimeOut } from "../util/fetchUtils";

// TODO Merge with useFetch (most code ist the same)
export function useFetchMultiple<T>(
  url: RequestInfo,
  parms?: RequestInit,
  errorHandle?: (err: Error) => void
): [T | undefined, () => void] {
  const [data, setData] = useState<T | undefined>();
  const [state, setState] = useState(false);

  const update = () => {
    setState(!state);
  };

  useEffect(() => {
    let isMounted = true;

    fetchTimeOut(url, parms, 5000)
      .then(handleResponse)
      .then((newData: any) => {
        if (isMounted) setData(newData);
      })
      .catch((err) => {
        if (isMounted && errorHandle) errorHandle(err);
      });

    return () => {
      isMounted = false;
    };
  }, [url, parms, errorHandle, state]);

  return [data, update];
}
