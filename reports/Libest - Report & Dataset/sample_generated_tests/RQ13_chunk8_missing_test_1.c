/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk8_missing_test_1.c
 */

#include <CUnit/CUnit.h>

/* External helpers and test harness symbols used by the existing tests */
extern void st_stop(void);
extern void us1005_start_server(int a, int b, int c, int d);
extern void st_enable_pop(void);
extern void st_disable_pop(void);
extern void st_set_csrattrs(const char *s);
extern void st_disable_csr_cb(void);
extern void us1005_easy_provision(const char *testname, const char *ip, int a, int b);
extern char *log_search_target;
extern int search_target_found;
extern const char *US1005_SERVER_IP;

/* Existing tests use this macro at top of functions; provide a no-op if not defined */
#ifndef LOG_FUNC_NM
#define LOG_FUNC_NM ;
#endif

static void rq13_chunk8_missing_test_1 (void)
{
    LOG_FUNC_NM
    ;

    /*
     * Case 1: Successful enrollment when CSR contains a valid challengePassword
     * that the server can validate (PoP present and valid).
     */
    st_stop();
    /* Start server with PoP enabled (fourth arg == 1 as in exemplars) */
    us1005_start_server(0, 0, 0, 1);

    /* Use default CSR attrs that include challengePassword (simulate valid PoP)
     * Note: existing harness expects st_set_csrattrs(NULL) to set defaults; we
     * supply a CSR attrs string here consistent with the st_set_csrattrs API
     * usage pattern from exemplars.
     */
    st_set_csrattrs(NULL);

    /* Verify client will include the challengePassword in the CSR */
    log_search_target = "Client will include challengePassword in CSR\0";
    search_target_found = 0;
    us1005_easy_provision("TC1005-validpop", US1005_SERVER_IP, 0, 0);
    CU_ASSERT(search_target_found == 1);

    /* Ensure the server did not log a PoP authentication failure for the valid PoP */
    log_search_target = "PoP enabled, CSR was not authenticated\0";
    search_target_found = 0;
    us1005_easy_provision("TC1005-validpop-check", US1005_SERVER_IP, 0, 0);
    /* If PoP validated correctly the failure message should NOT be emitted */
    CU_ASSERT(search_target_found == 0);

    /*
     * Case 2: Invalid PoP - CSR contains a challengePassword that does not
     * match the TLS UID.  The server should detect the bad PoP and log an
     * appropriate failure message (exercise the "PoP is not valid" path).
     */
    st_stop();
    us1005_start_server(0, 0, 0, 1);

    /* Set CSR attrs to a value that simulates an incorrect challengePassword
     * (the st_set_csrattrs API is used in exemplars to control CSR content).
     */
    st_set_csrattrs("CN=test-invalid-pop,challengePassword=BAD\0");

    /* Search for the server's PoP-invalid diagnostic message */
    log_search_target = "PoP is not valid\0";
    search_target_found = 0;
    us1005_easy_provision("TC1005-invalidpop", US1005_SERVER_IP, 0, 0);

    /* The server should have logged that the PoP was not valid */
    CU_ASSERT(search_target_found == 1);

    /*
     * Restore default CSR attrs and disable PoP for cleanup
     */
    st_set_csrattrs(NULL);
    st_disable_pop();
}
