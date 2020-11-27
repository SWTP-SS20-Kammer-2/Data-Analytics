import { useState, useEffect } from "react";
import { handleResponse, fetchTimeOut } from "../util/fetchUtils";

/**
 * Funktion um Json daten beim laden eines React Components zu bekommen.
 * Wird das Component entladen befor der Response da ist, wird der Response ignoriert.
 *
 * @param url Request URL (siehe fetch)
 * @param parms Request parms (siehe fetch)
 * @param errorHandle Callback Funktion für den Fehler fall
 */
export const useFetch = (
  url: RequestInfo,
  parms?: RequestInit,
  errorHandle?: (err: Error) => void
) => {
  const [data, setData] = useState<any>();

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
  }, [url, parms, errorHandle]);

  return data;
};
