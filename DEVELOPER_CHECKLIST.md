# Phase C Step 2: Developer Checklist

## Pre-Deployment Checklist

### ✅ Code Review

- [ ] Read `backend/llm/rule_engine.py` (understand RuleEngine class)
- [ ] Read `backend/api/recommendation.py` (understand API endpoints)
- [ ] Read `backend/worker/tasks/recommender.py` (understand Celery integration)
- [ ] Review test file `backend/tests/test_rule_engine.py`
- [ ] Check database model in `backend/models.py`

### ✅ Testing

- [ ] Run all tests: `pytest backend/tests/test_rule_engine.py -v`
- [ ] Expected result: `27 passed in 2.68s`
- [ ] Run end-to-end verification: `python verify_phase_c_step2.py`
- [ ] Expected result: `✓ PHASE C STEP 2 END-TO-END TEST PASSED`
- [ ] Test each API endpoint manually

### ✅ Documentation Review

- [ ] Read `PHASE_C_STEP2_INDEX.md` (navigation)
- [ ] Read `PHASE_C_STEP2_QUICK_REFERENCE.md` (quick start)
- [ ] Read `PHASE_C_STEP2_RULE_ENGINE.md` (complete guide)
- [ ] Read `FINAL_SUMMARY.md` (overview)

### ✅ Environment Setup

- [ ] PostgreSQL running
- [ ] Redis running
- [ ] Celery worker started
- [ ] Backend API running
- [ ] Environment variables set in `.env`

### ✅ Database Migration

- [ ] Run migrations: `alembic upgrade head`
- [ ] Verify ActionRecommendation table exists
- [ ] Check table schema matches documentation
- [ ] Verify indexes are created

### ✅ API Validation

- [ ] Test GET `/health` endpoint
- [ ] Test POST `/recommendation/test-rules` endpoint
- [ ] Verify JWT authentication works
- [ ] Check user isolation is enforced
- [ ] Verify all 6 endpoints respond

### ✅ Integration

- [ ] Celery task `generate_recommendation` registered
- [ ] Task triggers automatically after classification
- [ ] Email pipeline runs full flow: fetch → classify → recommend
- [ ] ActionRecommendation records created in database

### ✅ Backward Compatibility

- [ ] Phase B unchanged (email fetching works)
- [ ] Phase C Step 1 unchanged (classification works)
- [ ] No breaking changes to existing APIs
- [ ] All existing tests still pass

### ✅ Security

- [ ] JWT tokens validated
- [ ] Users can only see their own recommendations
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention verified
- [ ] Error messages don't leak sensitive data

### ✅ Performance

- [ ] Rule evaluation: <100ms per email
- [ ] API response: <200ms
- [ ] Celery task completes within timeout
- [ ] Database queries use indexes
- [ ] No N+1 query issues

### ✅ Monitoring

- [ ] Celery worker logs checked
- [ ] Database logs checked
- [ ] API error logs checked
- [ ] Task success rate monitored
- [ ] Performance metrics recorded

---

## Deployment Steps

### Step 1: Code Deployment

```bash
# Pull latest code
git pull

# Install/update dependencies (if any new)
pip install -r requirements.txt

# Run migrations
alembic upgrade head
```

### Step 2: Service Startup

```bash
# Terminal 1: PostgreSQL
docker-compose up postgres

# Terminal 2: Redis
docker-compose up redis

# Terminal 3: Celery worker
celery -A backend.worker.celery_app worker -l info

# Terminal 4: Backend API
uvicorn backend.main:app --reload --port 8000
```

### Step 3: Verification

```bash
# Run tests
pytest backend/tests/test_rule_engine.py -v

# Expected: 27 passed in 2.68s

# Run E2E verification
python verify_phase_c_step2.py

# Expected: ✓ PHASE C STEP 2 END-TO-END TEST PASSED
```

### Step 4: API Testing

```bash
# Test rule evaluation endpoint
curl -X POST http://localhost:8000/api/v1/recommendation/test-rules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "classification": "important",
    "confidence": 0.95,
    "sender": "test@example.com",
    "subject": "Test",
    "body": "Test"
  }'

# Expected: 200 response with recommendations
```

---

## Troubleshooting Guide

### Issue: Tests Failing

**Symptoms**: `pytest backend/tests/test_rule_engine.py` returns failures

**Solutions**:

1. Check PostgreSQL is running: `docker-compose up postgres`
2. Check migrations ran: `alembic upgrade head`
3. Check test database exists
4. Run with verbose output: `pytest -vvv`
5. Check database connection in logs

### Issue: Celery Tasks Not Running

**Symptoms**: No ActionRecommendation records created

**Solutions**:

1. Check Celery worker is running: `celery -A backend.worker.celery_app worker -l debug`
2. Check Redis is running: `docker-compose up redis`
3. Check task is registered: See worker logs for "Registered tasks"
4. Check `generate_recommendation` appears in registered tasks
5. Check email was classified first (has classification field)

### Issue: API Returns 401 Unauthorized

**Symptoms**: All API calls return 401

**Solutions**:

1. Check JWT token is valid
2. Check token is included in Authorization header
3. Check token hasn't expired
4. Check OPENAI_API_KEY is set in .env
5. Regenerate token if needed

### Issue: Low Confidence Scores

**Symptoms**: Confidence scores always <50%

**Solutions**:

1. Check classification confidence is high (should be 0.7+)
2. Check rule conditions match the email
3. Check sender/subject/body patterns match
4. Test with POST /test-rules endpoint to debug
5. Review rule definitions in code

### Issue: Pattern Matching Not Working

**Symptoms**: Sender patterns like "\*@company.com" not matching

**Solutions**:

1. Test pattern with POST /test-rules endpoint
2. Check pattern syntax: \* for wildcard, ? for single char
3. Check email address case (matching is case-insensitive)
4. Test with regex pattern as fallback
5. See documentation for pattern examples

### Issue: Database Error

**Symptoms**: `ProgrammingError` or `IntegrityError`

**Solutions**:

1. Check PostgreSQL is running
2. Run migrations: `alembic upgrade head`
3. Check database connection string in .env
4. Check ActionRecommendation table exists
5. Restart PostgreSQL and retry

---

## Performance Optimization

### If Evaluation Is Slow

1. Check database indexes are created
2. Profile with `cProfile`:
   ```python
   import cProfile
   cProfile.run('engine.evaluate(...)')
   ```
3. Check network latency to database
4. Batch process instead of single emails
5. Use task queue for background jobs

### If API Is Slow

1. Check database query performance
2. Add caching for rule loading
3. Use connection pooling
4. Monitor database CPU/memory
5. Scale with load balancer if needed

### If Task Queue Backs Up

1. Increase Celery concurrency: `-c 4` flag
2. Reduce countdown time if safe
3. Use dedicated Celery worker hosts
4. Monitor queue depth with Flower
5. Scale Redis if needed

---

## Maintenance Tasks

### Daily

- [ ] Check Celery worker logs for errors
- [ ] Monitor API response times
- [ ] Verify database is healthy
- [ ] Check for stuck tasks

### Weekly

- [ ] Review API error logs
- [ ] Check database space usage
- [ ] Verify backups are working
- [ ] Performance analysis

### Monthly

- [ ] Update dependencies (security patches)
- [ ] Review and optimize slow queries
- [ ] Analyze recommendation accuracy
- [ ] Plan Phase C Step 3 if needed

---

## Rollback Plan

If issues occur, rollback is safe because:

✅ No schema changes required (added new table only)  
✅ No modifications to existing code  
✅ Phase B and C Step 1 unaffected

### Rollback Steps

1. Stop Celery worker
2. Disable recommendation router in `main.py` (comment out 1 line)
3. Restart backend API
4. System falls back to Phase C Step 1 behavior

---

## Documentation Reference

| Document                         | Purpose     | Read Time |
| -------------------------------- | ----------- | --------- |
| FINAL_SUMMARY.md                 | Overview    | 5 min     |
| PHASE_C_STEP2_INDEX.md           | Navigation  | 5 min     |
| PHASE_C_STEP2_QUICK_REFERENCE.md | Quick start | 10 min    |
| PHASE_C_STEP2_RULE_ENGINE.md     | Complete    | 30 min    |
| PHASE_C_STEP2_COMPLETE.md        | Status      | 15 min    |
| PHASE_C_STEP2_DELIVERABLES.md    | Checklist   | 20 min    |
| COMPLETION_REPORT.md             | Sign-off    | 20 min    |

---

## Contact & Support

### Questions About Code?

→ See source code comments in `backend/llm/rule_engine.py`

### Questions About API?

→ See API docs: `http://localhost:8000/docs`

### Questions About Testing?

→ See `backend/tests/test_rule_engine.py`

### Questions About Rules?

→ See "Rule Definition" section in PHASE_C_STEP2_RULE_ENGINE.md

### Questions About Deployment?

→ See "Deployment Steps" section above

---

## Sign-Off

- [ ] All checks passed
- [ ] All tests passing (27/27)
- [ ] E2E verification passing
- [ ] Documentation reviewed
- [ ] Ready for production

**Status**: ✅ Ready to Deploy

---

## Next Actions

1. **Immediate** (today):

   - [ ] Review this checklist
   - [ ] Run tests
   - [ ] Verify environment

2. **Short-term** (this week):

   - [ ] Deploy to staging
   - [ ] Smoke test all endpoints
   - [ ] Monitor for issues

3. **Production** (next week):

   - [ ] Deploy to production
   - [ ] Monitor performance
   - [ ] Collect feedback

4. **Future** (optional):
   - [ ] Phase C Step 3 (action execution)
   - [ ] Custom rule builder
   - [ ] Analytics dashboard

---

**Checklist Version**: 1.0  
**Last Updated**: 2024  
**Status**: COMPLETE ✅

Print this checklist and check off items as you deploy!
