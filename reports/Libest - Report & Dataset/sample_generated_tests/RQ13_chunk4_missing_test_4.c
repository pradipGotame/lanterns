/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk4_missing_test_4.c
 */

static void rq13_chunk4_missing_test_4(void)
{
    long rv;

    LOG_FUNC_NM
    ;

    /*
     * Perform an enrollment over the HTTPS enroll endpoint.  Existing
     * tests demonstrate HTTP-layer success over TLS; verify we get 200.
     */
    rv = curl_http_post(US748_ENROLL_URL_BA, US748_PKCS10_CT,
                        US748_PKCS10_RSA2048,
                        US748_UIDPWD_GOOD, US748_CACERTS, CURLAUTH_BASIC, NULL, NULL, NULL);
    CU_ASSERT(rv == 200);

    /*
     * Attempt the same enroll over plain HTTP (no TLS).  The server
     * should not accept enrollment over plain HTTP; expect a non-200
     * result, demonstrating that TLS transport is required for enroll.
     * Use a direct http:// URL to avoid relying on project URL constants.
     */
    rv = curl_http_post("http://127.0.0.1:80/.well-known/est/enroll", US748_PKCS10_CT,
                        US748_PKCS10_RSA2048,
                        US748_UIDPWD_GOOD, NULL, CURLAUTH_BASIC, NULL, NULL, NULL);
    CU_ASSERT(rv != 200);
}
